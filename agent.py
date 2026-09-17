import os
import pandas as pd
import pypdf
import smtplib
from email.message import EmailMessage
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from google import genai

# ======================================================
# CONFIGURAÇÃO VISUAL DO PDF (FPDF)
# ======================================================
class PDFRelatorio(FPDF):
    def header(self):
        self.set_fill_color(44, 62, 80)
        self.rect(0, 0, 210, 30, 'F')
        self.set_font('helvetica', 'B', 15)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, 'Relatorio Automatico de Vendas', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        self.set_font('helvetica', '', 10)
        self.cell(0, 5, 'Analise Consolidada de Arquivos (Planilhas e PDFs)', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        self.ln(12)

# ======================================================
# 1. VARRER A PASTA E EXTRAIR O CONTEÚDO
# ======================================================

# Criar uma pasta nomeada como vendas dentro da pasta que estiver rodando o agente, e colocar os arquivos que deseja analizar dentro dela
# O agente lê arquivos PDF e XLSX
def extrair_conteudo_pasta(pasta="vendas"):
    if not os.path.exists(pasta):
        os.makedirs(pasta)
        print(f"A pasta '{pasta}' foi criada. Insira os arquivos nela.")
        return ""

    arquivos = os.listdir(pasta)
    if not arquivos:
        print(f"Nenhum arquivo encontrado na pasta '{pasta}'.")
        return ""

    conteudos = []

    for arquivo in arquivos:
        caminho_completo = os.path.join(pasta, arquivo)
        ext = arquivo.lower().split('.')[-1]

        print(f"Lendo o arquivo: {arquivo}...")

        if ext in ['xlsx', 'xls', 'csv']:
            try:
                df = pd.read_csv(caminho_completo) if ext == 'csv' else pd.read_excel(caminho_completo)
                conteudos.append(f"--- DADOS DA PLANILHA ({arquivo}) ---\n{df.to_string(index=False)}")
            except Exception as erro:
                print(f"Erro ao ler a planilha {arquivo}: {erro}")

        elif ext == 'pdf':
            try:
                leitor = pypdf.PdfReader(caminho_completo)
                texto_pdf = "\n".join([p.extract_text() for p in leitor.pages if p.extract_text()])
                conteudos.append(f"--- DADOS DO PDF ({arquivo}) ---\n{texto_pdf}")
            except Exception as erro:
                print(f"Erro ao ler o PDF {arquivo}: {erro}")

    return "\n\n".join(conteudos)


# ======================================================
# 2. PROCESSAR O RESUMO COM A IA DO GEMINI
# ======================================================
def gerar_resumo_gemini(dados_consolidados):
 
    try:
        # Colocar a chave API da Google_AI_Studio
        client = genai.Client(api_key="chave_API")
        
        prompt_sistema = (
            "Voce e um analista comercial senior. Crie um resumo executivo "
            "objetivo e bem estruturado sobre o desempenho de vendas. "
            "Evite usar acentos ou caracteres especiais complexos para garantir "
            "a compatibilidade com o gerador de PDF."
        )
        
        print("Conectando ao Gemini 3.6 Flash e gerando resumo...")
        
        
        resposta = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=f"{prompt_sistema}\n\nAnalise estes dados:\n{dados_consolidados}"
        )
        
        print("Resumo gerado com sucesso!")
        return resposta.text
    except Exception as erro_geracao:
        print(f"Erro na conexao com o Gemini. Detalhe exato: {erro_geracao}")
        return "Nao foi possivel gerar o resumo com a IA. Verifique a conexao ou a validade da chave API."

# ======================================================
# 3. GERAÇÃO AUTOMÁTICA DO PDF FINAL
# ======================================================
def gerar_relatorio_pdf(resumo_texto, caminho_saida="Relatorio_Final_Consolidado.pdf"):
    try:
        pdf = PDFRelatorio()
        pdf.add_page()
        
        pdf.set_font("helvetica", "B", 12)
        pdf.set_text_color(41, 128, 185)
        pdf.cell(0, 10, "Resumo Executivo do Relatorio (IA Gemini)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)
        
        pdf.set_font("helvetica", "", 10)
        pdf.set_text_color(51, 51, 51)
        
        texto_limpo = resumo_texto.encode('latin-1', 'replace').decode('latin-1')
        
        pdf.multi_cell(0, 6, texto_limpo)
        
        pdf.output(caminho_saida)
        print(f"Relatorio gerado com sucesso! Arquivo salvo como: {caminho_saida}")
        return caminho_saida
    except Exception as erro:
        print(f"Erro ao gerar o PDF: {erro}")
        return None

# ======================================================
# 4. ENVIO DO PDF POR E-MAIL
# ======================================================
def enviar_email(caminho_arquivo):
    # colocar emails que deseja 
    email_remetente = "@gmail.com"
    senha_app = "senha_APP"
    email_destino = "@gmail.com"

    msg = EmailMessage()
    msg['Subject'] = "Relatorio do Dia"
    msg['From'] = email_remetente
    msg['To'] = email_destino
    msg.set_content("Olá, Tudo bem?\n\nSegue em anexo o relatório do dia gerado automaticamente pelo nosso sistema.\n\nAtenciosamente.")

    try:
        with open(caminho_arquivo, 'rb') as f:
            dados_pdf = f.read()
            nome_arquivo = os.path.basename(caminho_arquivo)

        msg.add_attachment(dados_pdf, maintype='application', subtype='pdf', filename=nome_arquivo)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(email_remetente, senha_app)
            smtp.send_message(msg)
            
        print("E-mail com o relatorio enviado com sucesso!")
    except Exception as erro:
        print(f"Nao foi possivel enviar o e-mail. Verifique as credenciais. Detalhe do erro: {erro}")

# ======================================================
# EXECUÇÃO DO PROJETO
# ======================================================
if __name__ == "__main__":
    print("Iniciando a leitura da pasta 'vendas'...")
    dados = extrair_conteudo_pasta("vendas")

    if dados.strip():
        print("Sintetizando os dados com o Gemini...")
        resumo = gerar_resumo_gemini(dados)

        print("Gerando o documento em PDF...")
        arquivo_gerado = gerar_relatorio_pdf(resumo)
        
        if arquivo_gerado:
            print("Preparando o envio por e-mail...")
            enviar_email(arquivo_gerado)
    else:
        print("Processo encerrado. Verifique se ha arquivos na pasta 'vendas'.")