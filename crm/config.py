"""Constantes do CRM: etapas do funil, origens, tipos de interação e cores."""
from datetime import date, datetime
from zoneinfo import ZoneInfo

FUSO = ZoneInfo("America/Sao_Paulo")

ETAPAS = [
    ("novo", "Novo lead", "#8A97A8"),
    ("contato", "Contato feito", "#5B7BC9"),
    ("proposta", "Proposta enviada", "#2747A8"),
    ("negociacao", "Negociação", "#7A4CC2"),
    ("ganho", "Ganho", "#1C7C4E"),
    ("perdido", "Perdido", "#B4322B"),
]
ETAPA_NOME = {k: n for k, n, _ in ETAPAS}
ETAPA_COR = {k: c for k, _, c in ETAPAS}
ETAPA_IDS = [k for k, _, _ in ETAPAS]
ABERTAS = ["novo", "contato", "proposta", "negociacao"]

ORIGENS = ["Indicação", "Instagram", "WhatsApp", "Google", "Site", "Feira/Evento", "Outro"]

TIPOS = {
    "ligacao": "📞 Ligação",
    "whatsapp": "💬 WhatsApp",
    "email": "✉️ E-mail",
    "reuniao": "🤝 Reunião",
    "nota": "📝 Nota",
}


def agora() -> datetime:
    """Data e hora local (Brasília), sem fuso, para gravar no banco."""
    return datetime.now(FUSO).replace(tzinfo=None, microsecond=0)


def hoje() -> date:
    return agora().date()


def brl(valor) -> str:
    """Formata número como moeda brasileira: R$ 12.345."""
    try:
        v = float(valor or 0)
    except (TypeError, ValueError):
        v = 0.0
    return "R$ " + f"{v:,.0f}".replace(",", ".")


def data_br(d) -> str:
    if not d:
        return ""
    if isinstance(d, str):
        d = date.fromisoformat(d[:10])
    return d.strftime("%d/%m/%Y")


def rotulo_prazo(vence: date | None) -> str:
    if not vence:
        return ""
    h = hoje()
    if vence < h:
        return f"🔴 Atrasada · {data_br(vence)}"
    if vence == h:
        return "🟠 Hoje"
    return f"⚪ {data_br(vence)}"
