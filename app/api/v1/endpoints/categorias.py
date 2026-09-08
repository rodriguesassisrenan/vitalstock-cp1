from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.schemas import estoque_schemas
from app.services import estoque_service

router = APIRouter()

@router.get("/", response_model=List[estoque_schemas.Categoria])
def read_categorias(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return estoque_service.get_categorias(db, skip=skip, limit=limit)

@router.get("/{categoria_id}", response_model=estoque_schemas.Categoria)
def read_categoria(categoria_id: int, db: Session = Depends(get_db)):
    return estoque_service.get_categoria(db, categoria_id)

@router.post("/", response_model=estoque_schemas.Categoria, status_code=status.HTTP_201_CREATED)
def create_categoria(categoria: estoque_schemas.CategoriaCreate, db: Session = Depends(get_db)):
    return estoque_service.create_categoria(db, categoria)

@router.put("/{categoria_id}", response_model=estoque_schemas.Categoria)
def update_categoria(categoria_id: int, categoria_update: estoque_schemas.CategoriaUpdate, db: Session = Depends(get_db)):
    return estoque_service.update_categoria(db, categoria_id, categoria_update)

@router.delete("/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_categoria(categoria_id: int, db: Session = Depends(get_db)):
    estoque_service.delete_categoria(db, categoria_id)
