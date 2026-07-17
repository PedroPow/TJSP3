import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import random
import string
import re
import asyncio
import os

# ==============================================================================
# CONFIGURAÇÕES DO BOT E CARGOS
# ==============================================================================
TOKEN = os.getenv("TOKEN_TJSP")  # Substitua pelo token do seu bot
CANAL_LOGS_ID = 1526670983350718464  # Substitua pelo ID do canal de aprovação/logs

# Mapeamento dos cargos do Discord (Insira os IDs numéricos dos seus cargos)
ROLES = {
    # Prefeitura e Cidadão
    "CIDADÃO": 1526643628548817056,
    "PREFEITURA": 1526383985129947206,  # Cargo com acesso exclusivo para gerenciar Prefeitura
    
    # TJSP
    "Presidente": 1526388081077518456,
    "Vice Presidente": 1526388116774977626,
    "Administrador": 1526379218865229895,
    "Desembargador Geral": 1526384213278982174,
    "Juiz": 1526386991644807228,
    "Advogado": 1526386841694109847,
    "Promotor": 1526386906777260196,
    "Oficial de Justiça": 1526387360986566726,
    "Estagiário de Advocacia": 1526387373766606929,
    "Segurança": 1526387511755276369,
    
    # Policia Militar
    "[☫ ∗⁑] Comandante Geral da Policia Militar": 1527186659873919027,
    "[∥⁂∥] Sub Comandante Geral da Policia Militar": 1527186549349810216,
    "[✵✵✵] Coronel QOPM": 1527188175200456854,
    "[✵✵✧] Tenente Coronel QOPM": 1527188197233397900,
    "[✵✧✧] Major QOPM": 1527188216262955092,
    "[✧✧✧] Capitão QOPM": 1527188235409817640,
    
    # Policia Civil
    "Delegado Geral (PC)": 1526386653894279258,
    "Delegado (PC)": 1526386653894279258,
    "Delegado Adjunto (PC)": 1526386653894279258,
    
    # Policia Federal
    "Delegado Geral (PF)": 1526386752070353056,
    "Delegado (PF)": 1526386752070353056,
    "Delegado Adjunto (PF)": 1526386752070353056,
}

# Exemplo: ID do cargo que deve ser marcado nas logs (ex: Staff / Aprovadores)
CARGO_RESPONSAVEL_ID = 1526624858912461002  # Substitua pelo ID real do cargo

# ==============================================================================
# FUNÇÃO AUXILIAR PARA EMBEDS PADRÃO AMARELO
# ==============================================================================
def criar_embed_amarelo(titulo: str, descricao: str = None) -> discord.Embed:
    """Cria um Embed padronizado na cor amarela."""
    return discord.Embed(
        title=titulo,
        description=descricao,
        color=discord.Color.yellow()
    )

# ==============================================================================
# BANCO DE DADOS (SQLite)
# ==============================================================================
conn = sqlite3.connect("solicitacoes.db")
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS solicitacoes (
    codigo TEXT PRIMARY KEY,
    user_id INTEGER,
    nome TEXT,
    identificador TEXT,
    instituicao TEXT,
    cargo TEXT,
    status TEXT,
    processado_por INTEGER
)
''')
conn.commit()

def gerar_codigo():
    return '#' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

# ==============================================================================
# MODAL DE PREENCHIMENTO DE DADOS
# ==============================================================================
class ModalDados(discord.ui.Modal):
    def __init__(self, instituicao: str, cargo: str):
        super().__init__(title="Dados do Set")
        self.instituicao = instituicao
        self.cargo = cargo

        self.nome = discord.ui.TextInput(
            label="Nome",
            placeholder="Digite seu nome completo/RP",
            required=True,
            max_length=50
        )
        self.identificador = discord.ui.TextInput(
            label="Identificador (ID)",
            placeholder="Digite seu ID no jogo",
            required=True,
            max_length=15
        )

        self.add_item(self.nome)
        self.add_item(self.identificador)

    async def on_submit(self, interaction: discord.Interaction):
            codigo = gerar_codigo()
            
            cursor.execute('''
                INSERT INTO solicitacoes (codigo, user_id, nome, identificador, instituicao, cargo, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (codigo, interaction.user.id, self.nome.value, self.identificador.value, self.instituicao, self.cargo, 'PENDENTE'))
            conn.commit()

            canal_logs = interaction.guild.get_channel(CANAL_LOGS_ID)
            if not canal_logs:
                embed_erro = criar_embed_amarelo("❌ Erro no Sistema", "Canal de logs não foi encontrado. Contate a administração.")
                await interaction.response.send_message(embed=embed_erro, ephemeral=True)
                return

            # Embed enviado para o Canal de Logs
            embed_log = criar_embed_amarelo(f"<:assumirticket:1526748343978561547> Solicitação **{codigo}**", f"Uma nova solicitação foi recebida")

            embed_log.add_field(name="<:pessoas:1526764699490713662> Aberto por", value=f"**{interaction.user.mention} (`{interaction.user.id}`)**", inline=False)            
            embed_log.add_field(name="<:pessoas:1526764699490713662> Nome", value=f"`{self.nome.value}`", inline=False)
            embed_log.add_field(name="<:111:1526738453511934023> ID", value=f"`{self.identificador.value}`", inline=False)
            embed_log.add_field(name="<:paineladmin:1526748297564389558> Instituição", value=f"`{self.instituicao}`", inline=False)
            embed_log.add_field(name="<:111:1526738453511934023> Cargo", value=f"`{self.cargo}`", inline=False)
            embed_log.add_field(name="<:baixar:1526771301065162874> Status", value="`PENDENTE`", inline=False)
            embed_log.add_field(name="<:222:1526738486126972929> Código da Solicitação", value=f"`{codigo}`", inline=False)

            view = ViewAprovacao(codigo)

            # UNICO ENVIO (Menciona os cargos e envia o embed numa única mensagem)
            await canal_logs.send(
                content=f"<@&1526383985129947206> <@&{CARGO_RESPONSAVEL_ID}>",
                embed=embed_log, 
                view=view
            )        

            # Resposta privada ao usuário
            embed_sucesso = criar_embed_amarelo(
                "✅ Solicitação Enviada!", 
                f"Sua solicitação foi enviada com sucesso para análise.\n\n**Código da Solicitação:** `{codigo}`"
            )

            await interaction.response.send_message(embed=embed_sucesso, ephemeral=True)

# ==============================================================================
# SELECT MENU DE CARGOS
# ==============================================================================
class SelectCargo(discord.ui.Select):
    def __init__(self, instituicao: str, opcoes: list):
        self.instituicao = instituicao
        options = [discord.SelectOption(label=cargo, value=cargo) for cargo in opcoes]
        super().__init__(placeholder="Selecione o seu Cargo...", options=options)

    async def callback(self, interaction: discord.Interaction):
        cargo_escolhido = self.values[0]
        await interaction.response.send_modal(ModalDados(self.instituicao, cargo_escolhido))

class ViewCargo(discord.ui.View):
    def __init__(self, instituicao: str, opcoes: list):
        super().__init__(timeout=60)
        self.add_item(SelectCargo(instituicao, opcoes))

# ==============================================================================
# SELECT MENU DE INSTITUIÇÃO
# ==============================================================================
class SelectInstituicao(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="TJSP", emoji="<:TJSP:1527173718445654188> ", value="TJSP"),
            discord.SelectOption(label="PREFEITURA", emoji="<:PREFEITURA:1527173343495585833>", value="PREFEITURA"),
            discord.SelectOption(label="POLICIA MILITAR", emoji="<:PMESP:1527172485349380137> ", value="POLICIA MILITAR"),
            discord.SelectOption(label="POLICIA CIVIL", emoji="<:PCESP:1527173768802340984> ", value="POLICIA CIVIL"),
            discord.SelectOption(label="POLICIA FEDERAL", emoji="<:POLICIAFEDERAL:1527173809264787526> ", value="POLICIA FEDERAL"),
            discord.SelectOption(label="CIDADÃO", emoji="<:JARDIM_PERI:1527173159692931162>", value="CIDADÃO"),
        ]
        super().__init__(placeholder="Selecione sua Instituição...", options=options)

    async def callback(self, interaction: discord.Interaction):
        inst = self.values[0]

        if inst in ["CIDADÃO", "PREFEITURA"]:
            await interaction.response.send_modal(ModalDados(inst, inst))
            return

        cargos_map = {
            "TJSP": ["Presidente", "Vice Presidente", "Administrador", "Desembargador Geral", "Juiz", "Advogado", "Promotor", "Oficial de Justiça", "Estágiario de Advogado", "Segurança"],
            "POLICIA MILITAR": ["[☫ ∗⁑] Comandante Geral da Policia Militar", "[∥⁂∥] Sub Comandante Geral da Policia Militar", "[✵✵✵] Coronel QOPM", "[✵✵✧] Tenente Coronel QOPM", "[✵✧✧] Major QOPM", "[✧✧✧] Capitão QOPM"],
            "POLICIA CIVIL": ["Delegado Geral (PC)", "Delegado (PC)", "Delegado Adjunto (PC)"],
            "POLICIA FEDERAL": ["Delegado Geral (PF)", "Delegado (PF)", "Delegado Adjunto (PF)"]
        }

        view = ViewCargo(inst, cargos_map[inst])
        embed_cargo = criar_embed_amarelo(
            "💼 Seleção de Cargo",
            f"Você selecionou a instituição **{inst}**.\nEscolha o seu cargo no menu abaixo:"
        )
        await interaction.response.send_message(embed=embed_cargo, view=view, ephemeral=True)

class ViewInstituicao(discord.ui.View):
    def __init__(self, timeout=60):
        super().__init__(timeout=timeout)
        self.add_item(SelectInstituicao())

# ==============================================================================
# PAINEL PRINCIPAL (BOTÃO INICIAL)
# ==============================================================================
class ViewInicio(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Solicitar Set",  style=discord.ButtonStyle.secondary, emoji="<:assumirticket:1526748343978561547>", custom_id="btn_solicitar_set")
    async def solicitar_set(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed_inst = criar_embed_amarelo(
            "⚖️ Seleção de Instituição", 
            "Selecione a sua instituição no menu abaixo para continuar:"
        )
        await interaction.response.send_message(embed=embed_inst, view=ViewInstituicao(), ephemeral=True)

# ==============================================================================
# BOTOES DE APROVAÇÃO / REPROVAÇÃO (SISTEMA DE LOGS COM RESTRIÇÃO)
# ==============================================================================
class ViewAprovacao(discord.ui.View):
    def __init__(self, codigo: str = None):
        super().__init__(timeout=None)
        if codigo:
            self.aceitar.custom_id = f"aceitar_{codigo}"
            self.recusar.custom_id = f"recusar_{codigo}"

    async def _validar_permissao_prefeitura(self, interaction: discord.Interaction, instituicao: str) -> bool:
        """Verifica permissão exclusiva para aprovações/reprovações da Prefeitura"""
        if instituicao == "PREFEITURA":
            id_cargo_prefeitura = ROLES.get("PREFEITURA")
            tem_cargo = any(role.id == id_cargo_prefeitura for role in interaction.user.roles)
            if not tem_cargo:
                embed_negado = criar_embed_amarelo(
                    "🚫 Acesso Negado!", 
                    "Apenas membros com o cargo de **PREFEITURA** podem aprovar ou recusar solicitações desta instituição."
                )
                await interaction.response.send_message(embed=embed_negado, ephemeral=True)
                return False
        return True

    @discord.ui.button(label="Aceitar", style=discord.ButtonStyle.secondary, emoji="<:AMARELO:1527182949466767371> ")
    async def aceitar(self, interaction: discord.Interaction, button: discord.ui.Button):
        codigo = button.custom_id.split("_")[1]
        
        cursor.execute("SELECT user_id, nome, identificador, cargo, status, instituicao FROM solicitacoes WHERE codigo = ?", (codigo,))
        dados = cursor.fetchone()

        if not dados:
            embed_erro = criar_embed_amarelo("❌ Erro", "Solicitação não encontrada no banco de dados.")
            await interaction.response.send_message(embed=embed_erro, ephemeral=True)
            return

        user_id, nome_rp, id_game, cargo_nome, status, instituicao = dados

        if not await self._validar_permissao_prefeitura(interaction, instituicao):
            return

        if status != "PENDENTE":
            embed_aviso = criar_embed_amarelo("⚠️ Atenção", f"Esta solicitação já foi **{status}** anteriormente.")
            await interaction.response.send_message(embed=embed_aviso, ephemeral=True)
            return

        membro = interaction.guild.get_member(user_id)
        if not membro:
            embed_erro = criar_embed_amarelo("❌ Erro", "O membro solicitante não foi encontrado no servidor.")
            await interaction.response.send_message(embed=embed_erro, ephemeral=True)
            return

        # ALTERAÇÃO DO APELIDO (NICKNAME) NO SERVIDOR PARA O PADRÃO (Nome | ID)
        novo_nick = f"{nome_rp} | {id_game}"
        try:
            # Garante que o nickname não passe do limite do Discord (32 caracteres)
            if len(novo_nick) > 32:
                novo_nick = novo_nick[:32]
            await membro.edit(nick=novo_nick)
        except discord.Forbidden:
            print(f"⚠️ Sem permissão para alterar o apelido de {membro.display_name} (O cargo do bot precisa estar acima do membro ou o membro é o Dono do Servidor).")
        except Exception as e:
            print(f"⚠️ Erro ao tentar alterar o apelido: {e}")

        # REGRA ESPECIAL DE CARGOS DUPLOS DA PM
        if cargo_nome == "COMANDO GERAL":
            cargos_para_adicionar = ["COMANDO GERAL", "CORONEL PM"]
        elif cargo_nome == "SUB COMANDO GERAL":
            cargos_para_adicionar = ["SUB COMANDO GERAL", "TENENTE CORONEL PM"]
        else:
            cargos_para_adicionar = [cargo_nome]

        roles_add = []
        for c in cargos_para_adicionar:
            role_id = ROLES.get(c)
            if role_id:
                role = interaction.guild.get_role(role_id)
                if role:
                    roles_add.append(role)

        if roles_add:
            await membro.add_roles(*roles_add)

        cursor.execute("UPDATE solicitacoes SET status = 'ACEITO', processado_por = ? WHERE codigo = ?", (interaction.user.id, codigo))
        conn.commit()

        # Atualiza o Embed da Log
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.yellow()
        
        for i, field in enumerate(embed.fields):
            if field.name == "<:baixar:1526771301065162874> Status":
                embed.set_field_at(i, name="<:baixar:1526771301065162874> Status", value="`ACEITO`", inline=False)
        
        embed.add_field(name="<:ticketassumido:1526748366015565904>  Aceito por", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)

        embed_notif = criar_embed_amarelo("✅ Set Aprovado", f"O set de {membro.mention} foi aprovado com sucesso e seu nome foi alterado para `{novo_nick}`!")
        await interaction.followup.send(embed=embed_notif, ephemeral=True)

    @discord.ui.button(label="Reprovar", style=discord.ButtonStyle.secondary, emoji="<:x1:1527182368958316695>")
    async def recusar(self, interaction: discord.Interaction, button: discord.ui.Button):
        codigo = button.custom_id.split("_")[1]

        cursor.execute("SELECT user_id, status, instituicao FROM solicitacoes WHERE codigo = ?", (codigo,))
        dados = cursor.fetchone()

        if not dados:
            embed_erro = criar_embed_amarelo("❌ Erro", "Solicitação não encontrada.")
            await interaction.response.send_message(embed=embed_erro, ephemeral=True)
            return

        user_id, status, instituicao = dados

        if not await self._validar_permissao_prefeitura(interaction, instituicao):
            return

        if status != "PENDENTE":
            embed_aviso = criar_embed_amarelo("⚠️ Atenção", f"Esta solicitação já foi **{status}**.")
            await interaction.response.send_message(embed=embed_aviso, ephemeral=True)
            return

        cursor.execute("UPDATE solicitacoes SET status = 'RECUSADO', processado_por = ? WHERE codigo = ?", (interaction.user.id, codigo))
        conn.commit()

        # Atualiza o Embed da Log
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.yellow()
        
        for i, field in enumerate(embed.fields):
            if field.name == "<:baixar:1526771301065162874> Status":
                embed.set_field_at(i, name="<:baixar:1526771301065162874> Status", value="`RECUSADO`", inline=False)

        embed.add_field(name="<:111:1526738453511934023>  Recusado por", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)

        embed_notif = criar_embed_amarelo("❌ Set Recusado", "A solicitação foi recusada com sucesso.")
        await interaction.followup.send(embed=embed_notif, ephemeral=True)

# ==============================================================================
# SETUP DO BOT
# ==============================================================================
class SetBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(ViewInicio())
        
        cursor.execute("SELECT codigo FROM solicitacoes WHERE status = 'PENDENTE'")
        pendentes = cursor.fetchall()
        for p in pendentes:
            self.add_view(ViewAprovacao(codigo=p[0]))

bot = SetBot()

@bot.event
async def on_ready():
    print(f"✅ Bot online como {bot.user.name}")
    try:
        synced = await bot.tree.sync()
        print(f"🔗 {len(synced)} comandos Slash sincronizados.")
    except Exception as e:
        print(e)

# COMANDO SLASH E POR PREFIXO PARA ENVIAR O PAINEL
@bot.tree.command(name="setup_set", description="Envia a mensagem inicial do sistema de set.")
@app_commands.checks.has_permissions(administrator=True)
async def setup_set(interaction: discord.Interaction):
    embed_painel = criar_embed_amarelo(
        titulo="⚖️ Central de Atendimento Jurídico",
        descricao=
        "Seja bem-vindo(a) ao sistema de atendimento da Jardim Peri.\n"
        "Através do atendimento, você pode falar diretamente com nossa equipe.\n\n"
        "• Certifique-se de preencher seus dados de RP corretamente.\n\n"
         "**Horário de Atendimento:** 08:00 - 00:00"
    )

    embed_painel.set_image(url="https://cdn.discordapp.com/attachments/1444735189765849320/1526692086819328070/Criadores_JP_2.png?ex=6a5943ce&is=6a57f24e&hm=484f998b6d3387c061b1d67dd92235928c3d166c1798788fa9d0e4f2b6d2de18&")

    embed_painel.set_footer(text="TJSP Jardim Peri RP - Todos os direitos reservados © 2026", icon_url="https://cdn.discordapp.com/attachments/1444735189765849320/1526686691786752091/brasao_tjsp.webp?ex=6a593ec7&is=6a57ed47&hm=675a0a3d73ee60941aa54937e4ca85e84daa38622e0a70abf002cf659115cd59&")  

    await interaction.channel.send(embed=embed_painel, view=ViewInicio())
    
    embed_confirma = criar_embed_amarelo("✅ Sucesso", "Painel enviado no canal com sucesso!")
    await interaction.response.send_message(embed=embed_confirma, ephemeral=True)

@bot.command()
@commands.has_permissions(administrator=True)
async def TJSP1(ctx):
    embed_painel = criar_embed_amarelo(
        titulo="⚖️ Central de Atendimento Jurídico",
        descricao=
        "Seja bem-vindo(a) ao sistema de atendimento da Jardim Peri.\n"
        "Através do atendimento, você pode falar diretamente com nossa equipe.\n\n"
        "• Certifique-se de preencher seus dados de RP corretamente.\n\n"
        "**Horário de Atendimento:** 08:00 - 00:00"
    )

    embed_painel.set_image(url="https://cdn.discordapp.com/attachments/1444735189765849320/1526692086819328070/Criadores_JP_2.png?ex=6a5943ce&is=6a57f24e&hm=484f998b6d3387c061b1d67dd92235928c3d166c1798788fa9d0e4f2b6d2de18&")

    embed_painel.set_footer(text="TJSP Jardim Peri RP - Todos os direitos reservados © 2026", icon_url="https://cdn.discordapp.com/attachments/1444735189765849320/1526686691786752091/brasao_tjsp.webp?ex=6a593ec7&is=6a57ed47&hm=675a0a3d73ee60941aa54937e4ca85e84daa38622e0a70abf002cf659115cd59&")

    await ctx.send(embed=embed_painel, view=ViewInicio())

bot.run(TOKEN)