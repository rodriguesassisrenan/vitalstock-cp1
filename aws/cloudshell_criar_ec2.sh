#!/bin/bash
# Cria a EC2 e faz o deploy sem precisar de SSH. Feito para colar no AWS CloudShell.
#
#   bash aws/cloudshell_criar_ec2.sh
#
# Variáveis opcionais: BRANCH (padrão main), INSTANCE_TYPE (padrão t3.micro).
# A chave do Gemini é pedida sem aparecer na tela. Ela vai no user-data da instância,
# que só quem tem acesso a esta conta AWS consegue ler. Revogue a chave depois da avaliação.
set -euo pipefail

REPO="https://github.com/rodriguesassisrenan/vitalstock-cp1.git"
BRANCH="${BRANCH:-main}"
INSTANCE_TYPE="${INSTANCE_TYPE:-t3.micro}"
NOME="vitalstock"
REGION="$(aws configure get region || true)"
REGION="${REGION:-${AWS_REGION:-us-east-1}}"
export AWS_DEFAULT_REGION="$REGION"

read -rsp "Chave do Gemini (Enter para subir sem IA externa): " GEMINI_KEY
echo

echo "Região: $REGION | branch: $BRANCH | tipo: $INSTANCE_TYPE"

AMI=$(aws ssm get-parameter \
    --name /aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id \
    --query Parameter.Value --output text 2>/dev/null || true)
if [ -z "$AMI" ] || [ "$AMI" = "None" ]; then
    AMI=$(aws ec2 describe-images --owners 099720109477 \
        --filters "Name=name,Values=ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*" \
        --query 'sort_by(Images,&CreationDate)[-1].ImageId' --output text)
fi
echo "AMI Ubuntu 24.04: $AMI"

VPC=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text)
SG=$(aws ec2 describe-security-groups --filters Name=group-name,Values=${NOME}-sg Name=vpc-id,Values=$VPC \
    --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || true)
if [ -z "$SG" ] || [ "$SG" = "None" ]; then
    SG=$(aws ec2 create-security-group --group-name ${NOME}-sg --vpc-id "$VPC" \
        --description "VitalStock: so a porta 8000 aberta" --query GroupId --output text)
    aws ec2 authorize-security-group-ingress --group-id "$SG" --protocol tcp --port 8000 --cidr 0.0.0.0/0 > /dev/null
fi
echo "Security group: $SG (entrada só na porta 8000, sem SSH)"

USER_DATA=$(mktemp)
cat > "$USER_DATA" <<UD
#!/bin/bash
set -eu
apt-get update -y
apt-get install -y docker.io docker-compose-v2 git curl
systemctl enable --now docker
git clone --depth 1 --branch "$BRANCH" "$REPO" /opt/vitalstock
cd /opt/vitalstock
umask 077
printf 'GEMINI_API_KEY=%s\n' '$GEMINI_KEY' > .env
docker compose up -d --build
UD
unset GEMINI_KEY

PERFIL=()
if aws iam get-instance-profile --instance-profile-name LabInstanceProfile > /dev/null 2>&1; then
    PERFIL=(--iam-instance-profile Name=LabInstanceProfile)
fi

INSTANCE_ID=$(aws ec2 run-instances \
    --image-id "$AMI" \
    --instance-type "$INSTANCE_TYPE" \
    --security-group-ids "$SG" \
    "${PERFIL[@]}" \
    --metadata-options HttpTokens=required \
    --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=12,VolumeType=gp3,Encrypted=true}' \
    --user-data "file://$USER_DATA" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$NOME}]" \
    --query 'Instances[0].InstanceId' --output text)
rm -f "$USER_DATA"
echo "Instância criada: $INSTANCE_ID. Esperando ligar..."

aws ec2 wait instance-running --instance-ids "$INSTANCE_ID"
IP=$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
echo "IP público: $IP"
echo "Instalando Docker e construindo a imagem (leva uns 3 a 5 minutos)..."

for i in $(seq 1 60); do
    if curl -fs --max-time 5 "http://$IP:8000/health" > /dev/null; then
        echo
        curl -s "http://$IP:8000/health"; echo
        echo "Pronto."
        echo "Aplicação: http://$IP:8000/"
        echo "Swagger:   http://$IP:8000/docs"
        echo "Para desligar depois: aws ec2 terminate-instances --instance-ids $INSTANCE_ID"
        exit 0
    fi
    printf "."
    sleep 10
done

echo
echo "Não respondeu em 10 minutos. Log de inicialização da máquina:"
aws ec2 get-console-output --instance-id "$INSTANCE_ID" --latest --output text | tail -40
exit 1
