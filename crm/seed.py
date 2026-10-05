"""Dados de exemplo (fictícios) para demonstração. Todos ficam marcados como exemplo."""
from datetime import timedelta

from . import db
from .config import agora, hoje

CONTATOS = [
    ("Marina Albuquerque", "Padaria Trigo Bom", "(45) 99901-2201", "marina@trigobom.com.br", "Indicação", "negociacao", 4800, 20),
    ("Ricardo Tavares", "Auto Peças Oeste", "(45) 99812-3302", "compras@autopecasoeste.com.br", "Google", "proposta", 7200, 18),
    ("Fernanda Kloss", "Clínica Bem Viver", "(45) 99733-4403", "fernanda@bemviver.med.br", "Instagram", "contato", 3500, 13),
    ("Paulo Henrique Dias", "Transportadora Rota 277", "(45) 99654-5504", "paulo@rota277.com.br", "Feira/Evento", "novo", 12000, 1),
    ("Juliana Prates", "Ótica Visão Clara", "(45) 99545-6605", "juliana@visaoclara.com.br", "WhatsApp", "ganho", 2900, 25),
    ("Sérgio Ramalho", "Mercado Bom Preço", "(45) 99436-7706", "sergio@bompreco.com.br", "Indicação", "perdido", 5400, 30),
    ("Camila Nunes", "Studio Pilates Equilíbrio", "(45) 99327-8807", "camila@equilibrio.fit", "Site", "novo", 1800, 2),
    ("André Lemos", "Agro Insumos Lemos", "(45) 99218-9908", "andre@agrolemos.com.br", "Indicação", "ganho", 9600, 38),
]

# (índice do contato, tipo, texto, dias atrás, tarefa?, vence em N dias)
ATIVIDADES = [
    (0, "reuniao", "Reunião para alinhar escopo da planilha de controle de produção.", 2, False, None),
    (0, "ligacao", "Ligar para confirmar valor final da proposta.", 2, True, 0),
    (1, "email", "Proposta enviada por e-mail com 3 opções de pacote.", 3, False, None),
    (1, "whatsapp", "Cobrar retorno sobre a proposta.", 3, True, -1),
    (2, "whatsapp", "Primeiro contato; pediu exemplos de dashboards.", 1, False, None),
    (2, "email", "Enviar portfólio com exemplos de dashboards.", 1, True, 2),
    (3, "nota", "Conheci na feira; frota de 40 caminhões, quer controle de manutenção.", 1, False, None),
    (3, "ligacao", "Fazer ligação de apresentação.", 1, True, 1),
    (4, "reuniao", "Contrato assinado. Início do projeto na próxima semana.", 3, False, None),
    (5, "nota", "Optou por fazer internamente. Retomar contato em 6 meses.", 8, False, None),
]


def carregar_exemplos(responsavel_id: int | None = None) -> None:
    t = agora()
    ids = []
    for nome, emp, tel, email, orig, etapa, valor, dias in CONTATOS:
        criado = t - timedelta(days=dias)
        dados = dict(nome=nome, empresa=emp, telefone=tel, email=email, origem=orig, etapa=etapa,
                     valor=valor, responsavel_id=responsavel_id, notas="", exemplo=True,
                     criado_em=criado, atualizado_em=criado)
        if etapa == "ganho":
            dados["ganho_em"] = t - timedelta(days=3 if nome.startswith("Juliana") else 35)
        if etapa == "perdido":
            dados["motivo_perda"] = "Preço / fez internamente"
        ids.append(db.criar_contato(**dados))
    for i, tipo, texto, dias, tarefa, vence in ATIVIDADES:
        db.criar_atividade(ids[i], tipo, texto, tarefa=tarefa,
                           vence=(hoje() + timedelta(days=vence)) if tarefa else None,
                           usuario_id=responsavel_id, data=t - timedelta(days=dias), exemplo=True)
