from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.crud.consultations import consume_ip_rate, create_challenge, submit_consultation
from app.schemas.consultation import ChallengeResponse, ConsultationRequest, ConsultationResponse

router = APIRouter(prefix="/api/public/consultations", tags=["Đăng ký tư vấn công khai"])


def client_host(request):
    # Do not accept caller-provided X-Forwarded-For here. Configure trusted proxies
    # explicitly at the server if this app is deployed behind a reverse proxy.
    return request.client.host if request.client else "unknown"


def challenge_rate(request: Request, db: Session = Depends(get_db)):
    consume_ip_rate(db, client_host(request), "challenge")


def submission_rate(request: Request, db: Session = Depends(get_db)):
    consume_ip_rate(db, client_host(request), "submission")


@router.get("/challenge", response_model=ChallengeResponse, dependencies=[Depends(challenge_rate)])
def challenge(request: Request, response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    return create_challenge(db, client_host(request))


@router.post("", response_model=ConsultationResponse, status_code=201, dependencies=[Depends(submission_rate)])
def create_lead(data: ConsultationRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    created = submit_consultation(db, client_host(request), data)
    if not created:
        response.status_code = 200
    response.headers["Cache-Control"] = "no-store"
    return ConsultationResponse()
