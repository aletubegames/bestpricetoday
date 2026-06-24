"""
facebook.py — Callbacks para Meta/Facebook Data Deletion API

Rotas:
  POST /facebook/deletion-request  — Callback para solicitações de exclusão de dados da Meta
  GET  /facebook/deletion-status/{confirmation_code}  — Status da exclusão para o usuário
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel
import hmac
import hashlib
import base64
import json
import uuid
from datetime import datetime, timezone, timedelta
from app.core.logging import logger
from app.core.config import settings
from app.db.session import get_db
from app.models.models import User, DataDeletionRequest, PriceAlert, Favorite, Search, Analytics, AffiliateClick

router = APIRouter()


class DeletionRequestPayload(BaseModel):
    """Payload da solicitação de exclusão de dados da Meta"""
    url: str  # URL onde o usuário pode verificar o status
    confirmation_code: str  # Código único de confirmação


def parse_signed_request(signed_request: str) -> dict | None:
    """
    Decodifica e valida a solicitação assinada do Facebook.
    
    Args:
        signed_request: String no formato 'signature.payload'
    
    Returns:
        Dict com os dados decodificados ou None se inválido
    """
    try:
        # Separar assinatura e payload
        encoded_sig, payload = signed_request.split('.', 1)
        
        # Decodificar a assinatura e o payload
        sig = base64.urlsafe_b64decode(encoded_sig + '==')  # Adicionar padding se necessário
        data = json.loads(base64.urlsafe_b64decode(payload + '=='))
        
        # Validar a assinatura usando o app secret
        app_secret = settings.FACEBOOK_APP_SECRET or ""
        expected_sig = hmac.new(
            app_secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).digest()
        
        if sig != expected_sig:
            logger.error("❌ Assinatura inválida na solicitação de exclusão do Facebook")
            return None
        
        return data
    except Exception as e:
        logger.error(f"❌ Erro ao decodificar solicitação assinada: {e}")
        return None


@router.post("/deletion-request")
async def handle_deletion_request(request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    """
    Endpoint para receber solicitações de exclusão de dados da Meta.
    
    Este endpoint é acionado quando um usuário:
    1. Vai para Configurações e privacidade > Configurações > Aplicativos e sites do Facebook
    2. Encontra BestPriceToday
    3. Clica em "Remover"
    4. Clica em "Enviar solicitação"
    
    A Meta envia uma POST com um signed_request contendo o user_id (app-scoped) do usuário.
    """
    
    try:
        # Receber os dados do corpo da requisição
        form_data = await request.form()
        signed_request = form_data.get('signed_request')
        
        if not signed_request:
            logger.error("❌ Nenhum signed_request recebido")
            raise HTTPException(status_code=400, detail="missing signed_request")
        
        # Decodificar e validar a solicitação
        data = parse_signed_request(signed_request)
        if not data:
            raise HTTPException(status_code=400, detail="invalid signed_request")
        
        facebook_id = data.get('user_id')
        algorithm = data.get('algorithm')
        expires = data.get('expires')
        issued_at = data.get('issued_at')
        
        if not facebook_id:
            logger.error("❌ user_id não encontrado na solicitação")
            raise HTTPException(status_code=400, detail="missing user_id")
        
        logger.info(f"🔔 Solicitação de exclusão recebida para Facebook ID: {facebook_id}")
        logger.info(f"   Algoritmo: {algorithm}, Expira em: {expires}, Emitido em: {issued_at}")
        
        # ─────────────────────────────────────────────────────────────────────────────
        # IMPLEMENTAÇÃO REAL: Excluir dados do usuário
        # ─────────────────────────────────────────────────────────────────────────────
        
        # 1. Buscar o usuário pelo facebook_id (app-scoped)
        stmt = select(User).where(User.facebook_id == facebook_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        deleted_fields = {}
        
        if user:
            # 2. Coletar dados que serão excluídos
            original_email = user.email
            original_telegram_id = user.telegram_id
            
            # 3. Excluir relacionamentos do usuário
            # Deletar PriceAlerts
            await db.execute(delete(PriceAlert).where(PriceAlert.user_id == user.id))
            deleted_fields["price_alerts"] = "deleted"
            
            # Deletar Favorites
            await db.execute(delete(Favorite).where(Favorite.user_id == user.id))
            deleted_fields["favorites"] = "deleted"
            
            # Deletar Searches
            await db.execute(delete(Search).where(Search.user_id == user.id))
            deleted_fields["searches"] = "deleted"
            
            # Deletar AffiliateClicks
            await db.execute(delete(AffiliateClick).where(AffiliateClick.user_id == user.id))
            deleted_fields["affiliate_clicks"] = "deleted"
            
            # Deletar Analytics events
            await db.execute(delete(Analytics).where(Analytics.user_id == user.id))
            deleted_fields["analytics"] = "deleted"
            
            # 4. Limpar dados pessoais do usuário (soft delete)
            user.email = None
            user.telegram_id = None
            user.facebook_id = None
            user.name = None
            user.password_hash = None
            user.deleted_at = datetime.now(timezone.utc)
            user.is_active = False
            
            if original_email:
                deleted_fields["email"] = original_email
            if original_telegram_id:
                deleted_fields["telegram_id"] = original_telegram_id
            
            logger.info(f"✅ Dados do usuário {facebook_id} marcados para exclusão")
            logger.info(f"   Campos deletados: {deleted_fields}")
        else:
            logger.info(f"ℹ️  Usuário com Facebook ID {facebook_id} não encontrado no BD")
            logger.info(f"   Isso é esperado se o usuário nunca fez login via Facebook")
        
        # 5. Gerar código de confirmação único
        confirmation_code = str(uuid.uuid4().hex[:8].upper())
        
        # 6. Criar registro de auditoria
        deletion_request = DataDeletionRequest(
            user_id=user.id if user else None,
            facebook_id=facebook_id,
            confirmation_code=confirmation_code,
            source="facebook",
            status="completed",
            deleted_fields=deleted_fields,
            requested_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=365)  # Manter por 1 ano
        )
        
        db.add(deletion_request)
        
        # 7. Commit de todas as transações
        await db.commit()
        
        # 8. URL de status onde o usuário pode acompanhar a exclusão
        status_url = f"https://bestpricetoday.vercel.app/deletion-status?code={confirmation_code}"
        
        logger.info(f"✅ Exclusão de dados processada com sucesso!")
        logger.info(f"   Código de confirmação: {confirmation_code}")
        logger.info(f"   URL de status: {status_url}")
        
        # 9. Retornar resposta conforme especificado pela Meta
        response = {
            "url": status_url,
            "confirmation_code": confirmation_code
        }
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao processar solicitação de exclusão: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="internal server error")


@router.get("/deletion-status/{confirmation_code}")
async def get_deletion_status(
    confirmation_code: str,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Endpoint para o usuário verificar o status da sua solicitação de exclusão.
    
    Args:
        confirmation_code: Código de confirmação recebido na solicitação
    
    Returns:
        Status da exclusão (concluída, em andamento, não encontrada)
    """
    
    try:
        # 1. Buscar o registro de exclusão pelo confirmation_code
        stmt = select(DataDeletionRequest).where(
            DataDeletionRequest.confirmation_code == confirmation_code
        )
        result = await db.execute(stmt)
        deletion = result.scalar_one_or_none()
        
        if not deletion:
            logger.info(f"📋 Código de confirmação não encontrado: {confirmation_code}")
            return {
                "status": "not_found",
                "confirmation_code": confirmation_code,
                "message": "Código de confirmação não encontrado. "
                          "Verifique se digitou corretamente.",
                "help": "Entre em contato com aletubegames@gmail.com se tiver dúvidas"
            }
        
        # 2. Retornar status detalhado
        logger.info(f"📋 Status consultado para código: {confirmation_code}")
        
        response = {
            "status": deletion.status,
            "confirmation_code": confirmation_code,
            "requested_at": deletion.requested_at.isoformat() if deletion.requested_at else None,
            "completed_at": deletion.completed_at.isoformat() if deletion.completed_at else None,
            "source": deletion.source,
            "help": "Se tiver dúvidas, entre em contato com aletubegames@gmail.com"
        }
        
        # Adicionar mensagem apropriada baseada no status
        if deletion.status == "completed":
            response["message"] = "Seus dados foram excluídos com sucesso! "
            response["deleted_fields"] = deletion.deleted_fields or {}
        elif deletion.status == "processing":
            response["message"] = "Sua solicitação de exclusão de dados está sendo processada. "
            response["eta"] = "Você receberá uma confirmação em até 48 horas."
        elif deletion.status == "failed":
            response["message"] = f"Houve um erro ao processar sua solicitação: {deletion.deletion_error}"
            response["action"] = "Por favor, entre em contato com aletubegames@gmail.com com este código."
        
        return response
    
    except Exception as e:
        logger.error(f"❌ Erro ao buscar status de exclusão: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="internal server error")
