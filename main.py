import sys
import os
import subprocess
from datetime import datetime

import psycopg2
from kivy.lang import Builder
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager, FallOutTransition
from kivymd.app import MDApp
from kivymd.uix.button import MDFlatButton
from reportlab.lib import utils
from reportlab.pdfgen import canvas
import fitz
from dotenv import load_dotenv
from kivymd.uix.dialog import MDDialog

load_dotenv()


class ExportPDFPopup(Popup):
    pass


class ScreenGen(ScreenManager):
    def __init__(self, **kwargs):
        super(ScreenGen, self).__init__(**kwargs)
        self.transition = FallOutTransition()


class ScreenHome(Screen):
    pass


class ScreenData(Screen):
    pass


class MeuAplicativo(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Blue"
        return Builder.load_file('tela.kv')

    def on_start(self):
        self.mydb = psycopg2.connect(
            host=os.environ.get('HOST'),
            user=os.environ.get('USER'),
            password=os.environ.get('PASSWD'),
            dbname=os.environ.get('DATABASE'),
        )
        c = self.mydb.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS ex_servidores(
            id SERIAL PRIMARY KEY,
            cpf VARCHAR(18) NOT NULL,
            nome VARCHAR(255) NOT NULL,
            avos INTEGER NOT NULL,
            valor REAL NOT NULL,
            processo VARCHAR(25) NOT NULL,
            responsavellancamento VARCHAR(200) NOT NULL,
            saldoAtual REAL NOT NULL,
            dataEmissao TIMESTAMP
        )
        """)
        self.mydb.commit()

    def validate_date_format(value):
        try:
            parts = value.split('/')
            if len(parts) != 3:
                raise ValueError("Formato inválido. Use yyyy/mm/dd.")
            year, month, day = map(int, parts)
            if len(str(year)) != 4 or not 1 <= month <= 12 or not 1 <= day <= 31:
                raise ValueError("Data inválida.")
            return "Digite o padrão yyyy/mm/dd"
        except ValueError as e:
            return f"[color=#FF0000]{str(e)}[/color]"

    def submit(self):
        c = self.mydb.cursor()

        # Adicionar mais dados fictícios
        cpf = "98765432100"
        nome = "Ana Pereira"
        avos = 1
        valor = 2500.00
        processo = "PROC-2023-456"
        responsavellancamento = "Carlos Santos"
        saldoAtual = 1200.00
        c.execute(
            "INSERT INTO ex_servidores (cpf, nome, avos, valor, processo, responsavellancamento, saldoAtual) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (cpf, nome, avos, valor, processo, responsavellancamento, saldoAtual))

        self.mydb.commit()

    def search(self):
        result = ''
        c = self.mydb.cursor()
        sql_command = "SELECT * FROM ex_servidores WHERE cpf = %s"
        values_cpf = (self.root.get_screen('screenhome').ids.cpf_input.text,)
        c.execute(sql_command, values_cpf)
        result = c.fetchall()

        if result:
            self.root.current = 'screendata'
            for row in result:
                self.root.get_screen('screendata').ids.idCPF.text = row[1]
                self.root.get_screen('screendata').ids.idNome.text = row[2]
                self.root.get_screen('screendata').ids.idProcess.text = row[5]
                self.root.get_screen('screendata').ids.idRespLan.text = row[6]
                if row[8] is not None:
                    self.root.get_screen('screendata').ids.idDateI.text = str(row[8])
                else:
                    self.root.get_screen('screendata').ids.idDateI.text = "Não houve emissões!"
        else:
            # Criar e exibir o MDDialog com a mensagem de erro
            self.dialog = MDDialog(
                title='ERROR',
                text='Nenhum registro encontrado com o CPF informado',
                buttons=[MDFlatButton(text='Ok', on_release=self.liberar)]
            )
            self.dialog.open()

    def liberar(self, *args):
        # Fechar o MDDialog
        self.dialog.dismiss()

    def export_pdf(self):
        data = self.root.get_screen('screendata').ids
        c = self.mydb.cursor()
        sql_command = "SELECT * FROM ex_servidores WHERE cpf = %s"
        c.execute(sql_command, (data.idCPF.text,))
        result = c.fetchall()
        if result:
            for row in result:
                if row[8] is None:
                    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    c.execute("UPDATE ex_servidores SET dataEmissao = %s WHERE cpf = %s", (current_datetime, row[1]))
                    self.mydb.commit()
                    self.root.get_screen('screendata').ids.idDateI.text = current_datetime
        else:
            print("Nenhum dado encontrado")

        # Caminho do template
        template_path = 'nota-tecnica.pdf'

        # Converter o PDF em imagens
        pdf = fitz.open(template_path)
        page = pdf.load_page(0)
        pix = page.get_pixmap()
        pix.save("template_image.png")

        template_path_img = "template_image.png"

        img = utils.ImageReader(template_path_img)
        template_width, template_height = img.getSize()

        # Criar o arquivo PDF
        pdf = canvas.Canvas(f"dados-de-{data.idNome.text}.pdf", pagesize=(template_width, template_height))
        # Desenhar a imagem do template
        pdf.drawImage(img, 0, 0, width=template_width, height=template_height)
        # Escrever os registros no PDF
        y = template_height / 1  # Posição vertical inicial
        x = template_width / 14

        if result:
            for row in result:
                avos_do_banco = row[3]
                valor_do_banco = row[4]

        # Adicionar o texto do precatório do FUNDEF
        pdf.drawString(x + 20, y - 150, "O Estado do Amazonas recebeu do Governo Federal o valor total de R$")
        pdf.drawString(x, y - 162, "98.798.842,00 (noventa e oito milhões, setecentos e noventa e oito mil, oitocentos e")
        pdf.drawString(x, y - 174, "quarenta e dois reais), referente aos precatórios do FUNDEF, dos quais R$")
        pdf.drawString(x, y - 186, "59.279.305,22 (cinquenta e nove milhões, duzentos e setenta e nove mil, trezentos e")
        pdf.drawString(x, y - 198, "cinco reais e vinte e dois centavos), equivalentes a 60% do valor total, foram")
        pdf.drawString(x, y - 210, "destinados ao rateio entre os profissionais do magistério, conforme determina a Lei")
        pdf.drawString(x, y - 222, "Estadual nº 6.033, de 11 de agosto de 2022, no período de 1998 a 2007.")

        # 2 paragrafo
        pdf.drawString(x + 20, y - 246, "Destarte, foi rateado em forma de Abono, em caráter indenizatório, o valor de")
        pdf.drawString(x, y - 258, "R$ 59.279.305,22 (cinquenta e nove milhões, duzentos e setenta e nove mil,")
        pdf.drawString(x, y - 270, "trezentos e cinco reais e vinte e dois centavos), a partir da seguinte metodologia de cálculo:")

        # 3 paragrafo
        pdf.drawString(x + 20, y - 294, "-Foi extraído do Sistema de Cadastro de Folha de Pagamento de Pessoal –")
        pdf.drawString(x, y - 306, "CFPP/PRODAM o quantitativo de profissionais do magistério que perceberam")
        pdf.drawString(x, y - 318, "vencimentos no período estipulado pela supracitada Lei, levando em consideração")
        pdf.drawString(x, y - 330, "todas as matrículas funcionais laboradas pelo profissional. ")

        # 4 paragrafo
        pdf.drawString(x + 20, y - 354, "-Em seguida, foram identificados os meses de efetivo exercício nas funções,")
        pdf.drawString(x, y - 366, "considerando todas as respectivas matrículas funcionais dos profissionais do")
        pdf.drawString(x, y - 378, "magistério. Esta identificação possibilitou chegarmos ao quantitativo total de")
        pdf.drawString(x, y - 390, "2.479.268 (dois milhões, quatrocentos e setenta e nove mil, duzentos e sessenta e")
        pdf.drawString(x, y - 402, "oito) avos (meses) efetivamente trabalhados pelos 26.637 (vinte e seis mil,")
        pdf.drawString(x, y - 414, "seiscentos e trinta e sete) profissionais do magistério contemplados.")

        # 5 paragrafo
        pdf.drawString(x + 20, y - 438, "Posteriormente, o percentual de rateio determinado em Lei, totalizando o valor")
        pdf.drawString(x, y - 450, "de R$ 59.279.305,22 (cinquenta e nove milhões, duzentos e setenta e nove mil,")
        pdf.drawString(x, y - 462, "trezentos e cinco reais e vinte e dois centavos) foi dividido pelo total de 2.479.268")
        pdf.drawString(x, y - 474, "(dois milhões, quatrocentos e setenta e nove mil, duzentos e sessenta e oito) avos")
        pdf.drawString(x, y - 486, "(meses) efetivamente trabalhados pelos 26.637 (vinte e seis mil, seiscentos e trinta e")
        pdf.drawString(x, y - 498, "sete) profissionais do magistério contemplados, possibilitando, então, determinarmos")
        pdf.drawString(x, y - 510, "o valor a ser pago de R$ 23,91 (vinte e três reais e noventa e um centavos),")
        pdf.drawString(x, y - 522, "correspondente a 1 (um) mês de efetivo exercício.")

        # 6 paragrafo
        pdf.drawString(x + 20, y - 546, "Por fim, já com a identificação individual de cada profissional do magistério e")
        pdf.drawString(x, y - 558, "respectivos avos (meses) efetivamente trabalhados, foi realizada a multiplicação")
        pdf.drawString(x, y - 570, "entre o total de avos (meses) trabalhados e o valor de R$ 23,91 (vinte e três reais e")
        pdf.drawString(x, y - 582, "noventa e um centavos) que corresponde a 1 (um) mês trabalhado. Dessa forma,")
        pdf.drawString(x, y - 594, "chegamos ao valor total individual referente a todas as matrículas trabalhadas por")
        pdf.drawString(x, y - 606, "cada profissional do magistério a ser percebido em um único pagamento.")

        # 7 paragrafo
        pdf.drawString(x + 20, y - 630, "Diante do exposto e após consultas realizadas no sistema CFPP / PRODAM, o")
        pdf.drawString(x, y - 642, "Departamento de Gestão de Pessoas - DGP declara que o(a) senhor(a)")
        pdf.drawString(x, y - 654, f"{data.idNome.text} CPF {data.idCPF.text} exerceu suas atividades laborais")
        pdf.drawString(x, y - 666, "nesta Secretaria de Educação e Desporto, no período especificado pelas Leis")
        pdf.drawString(x, y - 678, "nº14.325, de 12 de abril de 2022 e nº 6.033, de 11 de agosto de 2022, tendo direito à")
        pdf.drawString(x, y - 690, f"percepção de {avos_do_banco} avos(meses), totalizando R$ {valor_do_banco}")

        pdf.save()
        pdf_path = f"dados-de-{data.idNome.text}.pdf"
        popup = ExportPDFPopup()
        popup.pdf_path = pdf_path
        popup.open()

    def open_pdf(self, file_path):
        if sys.platform.startswith('linux'):
            subprocess.Popen(['xdg-open', file_path])
        elif sys.platform.startswith('win32'):
            os.startfile(file_path)
        else:
            subprocess.Popen(['open', file_path])


MeuAplicativo().run()
