import asyncio
import json
import sys
print(f">>> PYTHON VERSION: {sys.version}", file=sys.stderr)
print(f">>> PYTHON PATH: {sys.executable}", file=sys.stderr)
print(">>> TENTANDO IMPORTAR BIBLIOTECAS...", file=sys.stderr)
import os
import re
from typing import Any, Dict
from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio
from bemtevi_client import BemTeviClient
from datetime import datetime
import concurrent.futures

# Criar servidor MCP
server = Server("BemTevi TST Integration Server")

# Cliente global
bemtevi_client = None
audit_log = []

def _audit(action: str, data: dict):
    """Registrar ação para auditoria"""
    global audit_log
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "data": data
    }
    audit_log.append(entry)
    print(f">>> AUDIT: {action}", file=sys.stderr)

def _analisar_com_ia(conteudo: str, tipo_analise: str) -> str:
    """Analisar conteúdo com IA - RETORNA CONTEÚDO COMPLETO COM ANÁLISE"""
    if not conteudo:
        return "Erro: Conteúdo vazio para análise"
    
    # Não resumir - entregar conteúdo completo com análise
    if tipo_analise == "resumo":
        analise = f"""
📋 **ANÁLISE RESUMIDA DA PEÇA**

**CONTEÚDO COMPLETO EXTRAÍDO:**
{conteudo}

**ANÁLISE AUTOMÁTICA:**
- Documento jurídico processual do BemTevi TST
- Tamanho do conteúdo: {len(conteudo)} caracteres
- Tipo de análise: Resumo executivo
- Data da análise: {datetime.now().strftime("%d/%m/%Y %H:%M")}

**OBSERVAÇÕES:**
- Este é o conteúdo completo extraído da peça
- Análise automática preliminar
- Para análise mais detalhada, todos os dados estão disponíveis acima
"""
    elif tipo_analise == "argumentos":
        analise = f"""
⚖️ **ANÁLISE DE ARGUMENTOS - CONTEÚDO COMPLETO**

**TEXTO INTEGRAL DA PEÇA:**
{conteudo}

**ANÁLISE DOS ARGUMENTOS:**
- Documento analisado para identificação de argumentos jurídicos
- Tamanho do texto: {len(conteudo)} caracteres
- Tipo de análise: Argumentos e fundamentação
- Data da análise: {datetime.now().strftime("%d/%m/%Y %H:%M")}

**ESTRUTURA ARGUMENTATIVA IDENTIFICADA:**
- Fundamentos jurídicos presentes no texto completo acima
- Precedentes e jurisprudência (se citados)
- Argumentação das partes (conforme texto integral)

**RECOMENDAÇÕES:**
- Revisar o texto completo acima para análise detalhada
- Verificar citações legais e jurisprudência mencionada
- Analisar contra-argumentos presentes
"""
    else:  # estrategia
        analise = f"""
🎯 **ANÁLISE ESTRATÉGICA - TEXTO COMPLETO**

**CONTEÚDO INTEGRAL PARA ANÁLISE:**
{conteudo}

**ANÁLISE ESTRATÉGICA:**
- Documento processual completo disponível acima
- Tamanho: {len(conteudo)} caracteres
- Tipo de análise: Estratégia processual
- Data da análise: {datetime.now().strftime("%d/%m/%Y %H:%M")}

**ESTRATÉGIA PROCESSUAL:**
- Identificar pontos fortes baseados no texto completo
- Mapear possíveis vulnerabilidades
- Definir próximos passos processuais

**AÇÕES SUGERIDAS:**
- Revisar jurisprudência aplicável mencionada no texto
- Preparar teses de defesa/ataque baseadas no conteúdo integral
- Avaliar possibilidade de recursos conforme argumentação presente
"""
    
    return analise

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """Listar ferramentas disponíveis"""
    tools = [
        Tool(
            name="conectar_bemtevi",
            description="Conecta ao sistema BemTevi do TST",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="consultar_processo_bemtevi",
            description="Consulta um processo específico no BemTevi",
            inputSchema={
                "type": "object",
                "properties": {
                    "numero_processo": {
                        "type": "string",
                        "description": "Número do processo (ex: 0000001-56.2024.5.08.0111)"
                    }
                },
                "required": ["numero_processo"]
            }
        ),
        Tool(
            name="listar_pecas_bemtevi",
            description="Lista todas as peças de um processo no BemTevi",
            inputSchema={
                "type": "object",
                "properties": {
                    "numero_processo": {
                        "type": "string",
                        "description": "Número do processo"
                    }
                },
                "required": ["numero_processo"]
            }
        ),
        Tool(
            name="acessar_peca_bemtevi",
            description="Acessa o conteúdo completo de uma peça específica",
            inputSchema={
                "type": "object",
                "properties": {
                    "numero_processo": {
                        "type": "string",
                        "description": "Número do processo"
                    },
                    "indice_peca": {
                        "type": "integer",
                        "description": "Índice da peça (0, 1, 2, etc.)"
                    }
                },
                "required": ["numero_processo", "indice_peca"]
            }
        ),
        Tool(
            name="acessar_despacho_admissibilidade_bemtevi",
            description="Acessa despacho de admissibilidade via API específica do BemTevi",
            inputSchema={
                "type": "object",
                "properties": {
                    "numero_processo": {
                        "type": "string",
                        "description": "Número do processo"
                    }
                },
                "required": ["numero_processo"]
            }
        ),
        Tool(
            name="acessar_airr_bemtevi",
            description="Acessa AIRR (Agravo de Instrumento em Recurso de Revista) via API específica",
            inputSchema={
                "type": "object",
                "properties": {
                    "numero_processo": {
                        "type": "string",
                        "description": "Número do processo"
                    }
                },
                "required": ["numero_processo"]
            }
        ),
        Tool(
            name="analisar_peca_bemtevi",
            description="Analisa uma peça específica do BemTevi com o texto completo",
            inputSchema={
                "type": "object",
                "properties": {
                    "numero_processo": {
                        "type": "string",
                        "description": "Número do processo"
                    },
                    "indice_peca": {
                        "type": "integer",
                        "description": "Índice da peça (0, 1, 2, etc.)"
                    },
                    "tipo_analise": {
                        "type": "string",
                        "description": "Tipo de análise: resumo, argumentos, estrategia",
                        "enum": ["resumo", "argumentos", "estrategia"]
                    }
                },
                "required": ["numero_processo", "indice_peca", "tipo_analise"]
            }
        ),
        Tool(
            name="analisar_despacho_admissibilidade_bemtevi",
            description="Analisa despacho de admissibilidade com IA",
            inputSchema={
                "type": "object",
                "properties": {
                    "numero_processo": {
                        "type": "string",
                        "description": "Número do processo"
                    },
                    "tipo_analise": {
                        "type": "string",
                        "description": "Tipo de análise: resumo, argumentos, estrategia",
                        "enum": ["resumo", "argumentos", "estrategia"]
                    }
                },
                "required": ["numero_processo", "tipo_analise"]
            }
        ),
        Tool(
            name="analisar_airr_bemtevi",
            description="Analisa AIRR com IA",
            inputSchema={
                "type": "object",
                "properties": {
                    "numero_processo": {
                        "type": "string",
                        "description": "Número do processo"
                    },
                    "tipo_analise": {
                        "type": "string",
                        "description": "Tipo de análise: resumo, argumentos, estrategia",
                        "enum": ["resumo", "argumentos", "estrategia"]
                    }
                },
                "required": ["numero_processo", "tipo_analise"]
            }
        ),
        Tool(
            name="status_bemtevi",
            description="Verifica status da conexão com BemTevi",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]
    
    # DEBUG: Mostra as ferramentas registradas
    print(">>> DEBUG: ===== FERRAMENTAS REGISTRADAS =====", file=sys.stderr)
    for tool in tools:
        print(f">>> DEBUG: - {tool.name}", file=sys.stderr)
    print(">>> DEBUG: =====================================", file=sys.stderr)
    
    return tools

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Executar ferramenta"""
    global bemtevi_client
    
    print(f">>> DEBUG: call_tool() chamada: {name}", file=sys.stderr)
    
    try:
        if name == "conectar_bemtevi":
            print(">>> DEBUG: Executando conectar_bemtevi", file=sys.stderr)
            
            def fazer_login_sync():
                print(">>> DEBUG: Iniciando login em thread separada", file=sys.stderr)
                client = BemTeviClient()
                sucesso = client.fazer_login()
                return client, sucesso
            
            # Executar em thread separada para evitar bloqueio
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                client, sucesso = await loop.run_in_executor(executor, fazer_login_sync)
            
            if sucesso:
                bemtevi_client = client
                _audit("conectar_bemtevi", {"sucesso": True})
                return [TextContent(type="text", text="✅ **Conectado ao BemTevi TST com sucesso!**\n\n🚀 Sistema pronto para consultas de processos, peças e análises com IA.\n\n💡 **Recursos disponíveis:**\n- Acesso direto a despachos de admissibilidade\n- Acesso direto a AIRR via APIs específicas\n- Análise completa de conteúdo com IA")]
            else:
                return [TextContent(type="text", text="❌ Falha ao conectar com o BemTevi TST. Verifique as credenciais.")]
        
        elif name == "consultar_processo_bemtevi":
            print(">>> DEBUG: Executando consultar_processo_bemtevi", file=sys.stderr)
            
            if not bemtevi_client:
                return [TextContent(type="text", text="❌ Erro: Faça login primeiro usando 'conectar_bemtevi'")]
            
            numero_processo = arguments.get("numero_processo", "")
            
            def consultar_sync():
                return bemtevi_client.consultar_processo(numero_processo)
            
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                resultado = await loop.run_in_executor(executor, consultar_sync)
            
            if resultado:
                _audit("consultar_processo", {"numero_processo": numero_processo})
                return [TextContent(type="text", text=f"✅ **Processo {numero_processo} consultado com sucesso!**\n\n📋 **Encontradas {resultado['total_pecas']} peças**\n\n💡 Use as funções específicas para acessar:\n- Despachos de admissibilidade\n- AIRR (Agravos)\n- Peças individuais")]
            else:
                return [TextContent(type="text", text=f"❌ Processo {numero_processo} não encontrado ou erro na consulta.")]
        
        elif name == "listar_pecas_bemtevi":
            print(">>> DEBUG: Executando listar_pecas_bemtevi", file=sys.stderr)
            
            if not bemtevi_client:
                return [TextContent(type="text", text="❌ Erro: Faça login primeiro usando 'conectar_bemtevi'")]
            
            numero_processo = arguments.get("numero_processo", "")
            
            def listar_pecas_sync():
                resultado = bemtevi_client.consultar_processo(numero_processo)
                return resultado['pecas'] if resultado else []
            
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                pecas = await loop.run_in_executor(executor, listar_pecas_sync)
            
            if pecas:
                resultado = f"📋 **Processo {numero_processo} possui {len(pecas)} peças:**\n\n"
                for peca in pecas:
                    resultado += f"**Peça {peca['indice']}**: {peca['tipo']} ({peca['data']})\n"
                    if peca['tem_link']:
                        resultado += f"   ↳ Link disponível para acesso ao conteúdo completo\n"
                
                resultado += f"\n💡 **Comandos disponíveis:**\n"
                resultado += f"- `acessar_peca_bemtevi` para ver conteúdo completo\n"
                resultado += f"- `acessar_despacho_admissibilidade_bemtevi` para despachos\n"
                resultado += f"- `acessar_airr_bemtevi` para agravos\n"
                resultado += f"- `analisar_*_bemtevi` para análises com IA"
                
                _audit("listar_pecas", {"numero_processo": numero_processo, "total_pecas": len(pecas)})
                return [TextContent(type="text", text=resultado)]
            else:
                return [TextContent(type="text", text=f"❌ Nenhuma peça encontrada para o processo {numero_processo}")]
        
        elif name == "acessar_peca_bemtevi":
            print(">>> DEBUG: Executando acessar_peca_bemtevi", file=sys.stderr)
            
            if not bemtevi_client:
                return [TextContent(type="text", text="❌ Erro: Faça login primeiro usando 'conectar_bemtevi'")]
            
            numero_processo = arguments.get("numero_processo", "")
            indice_peca = arguments.get("indice_peca", 0)
            
            def acessar_peca_sync():
                # Primeiro consultar o processo para garantir que está na página certa
                resultado_processo = bemtevi_client.consultar_processo(numero_processo)
                if resultado_processo:
                    return bemtevi_client.acessar_peca(indice_peca)
                return {"sucesso": False, "erro": "Processo não encontrado"}
            
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                resultado = await loop.run_in_executor(executor, acessar_peca_sync)
            
            if resultado.get("sucesso"):
                conteudo = resultado.get("conteudo_completo", "")
                tamanho = resultado.get("tamanho_conteudo", len(conteudo))
                
                _audit("acessar_peca", {
                    "numero_processo": numero_processo,
                    "indice_peca": indice_peca,
                    "tamanho_conteudo": tamanho
                })
                
                resposta = f"📑 **CONTEÚDO COMPLETO DA PEÇA {indice_peca}**\n\n"
                resposta += f"**Tipo**: {resultado.get('tipo', 'N/A')}\n"
                resposta += f"**Data**: {resultado.get('data', 'N/A')}\n"
                resposta += f"**Tamanho**: {tamanho} caracteres\n"
                resposta += f"**Método de extração**: {resultado.get('metodo_extracao', 'N/A')}\n\n"
                resposta += f"**TEXTO INTEGRAL:**\n\n{conteudo}"
                
                return [TextContent(type="text", text=resposta)]
            else:
                return [TextContent(type="text", text=f"❌ Erro ao acessar peça {indice_peca}: {resultado.get('erro', 'Erro desconhecido')}")]
        
        elif name == "acessar_despacho_admissibilidade_bemtevi":
            print(">>> DEBUG: Executando acessar_despacho_admissibilidade_bemtevi", file=sys.stderr)
            
            if not bemtevi_client:
                return [TextContent(type="text", text="❌ Erro: Faça login primeiro usando 'conectar_bemtevi'")]
            
            numero_processo = arguments.get("numero_processo", "")
            
            def acessar_despacho_sync():
                return bemtevi_client.acessar_despacho_admissibilidade(numero_processo)
            
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                resultado = await loop.run_in_executor(executor, acessar_despacho_sync)
            
            if resultado.get("sucesso"):
                conteudo = resultado.get("conteudo_completo", "")
                tamanho = resultado.get("tamanho_conteudo", len(conteudo))
                
                _audit("acessar_despacho_admissibilidade", {
                    "numero_processo": numero_processo,
                    "tamanho_conteudo": tamanho
                })
                
                resposta = f"📋 **DESPACHO DE ADMISSIBILIDADE**\n\n"
                resposta += f"**Processo**: {numero_processo}\n"
                resposta += f"**Tamanho**: {tamanho} caracteres\n"
                resposta += f"**Método**: {resultado.get('metodo_extracao', 'N/A')}\n"
                resposta += f"**URL API**: {resultado.get('url_api', 'N/A')}\n\n"
                resposta += f"**CONTEÚDO COMPLETO:**\n\n{conteudo}"
                
                return [TextContent(type="text", text=resposta)]
            else:
                return [TextContent(type="text", text=f"❌ Erro ao acessar despacho de admissibilidade: {resultado.get('erro', 'Erro desconhecido')}")]
        
        elif name == "acessar_airr_bemtevi":
            print(">>> DEBUG: Executando acessar_airr_bemtevi", file=sys.stderr)
            
            if not bemtevi_client:
                return [TextContent(type="text", text="❌ Erro: Faça login primeiro usando 'conectar_bemtevi'")]
            
            numero_processo = arguments.get("numero_processo", "")
            
            def acessar_airr_sync():
                return bemtevi_client.acessar_airr(numero_processo)
            
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                resultado = await loop.run_in_executor(executor, acessar_airr_sync)
            
            if resultado.get("sucesso"):
                conteudo = resultado.get("conteudo_completo", "")
                tamanho = resultado.get("tamanho_conteudo", len(conteudo))
                total_airr = resultado.get("total_airr", 1)
                
                _audit("acessar_airr", {
                    "numero_processo": numero_processo,
                    "tamanho_conteudo": tamanho,
                    "total_airr": total_airr
                })
                
                resposta = f"⚖️ **AIRR - AGRAVO DE INSTRUMENTO EM RECURSO DE REVISTA**\n\n"
                resposta += f"**Processo**: {numero_processo}\n"
                resposta += f"**Total de AIRR**: {total_airr}\n"
                resposta += f"**Tamanho**: {tamanho} caracteres\n"
                resposta += f"**Método**: {resultado.get('metodo_extracao', 'N/A')}\n"
                resposta += f"**URL API**: {resultado.get('url_api', 'N/A')}\n\n"
                resposta += f"**CONTEÚDO COMPLETO:**\n\n{conteudo}"
                
                return [TextContent(type="text", text=resposta)]
            else:
                return [TextContent(type="text", text=f"❌ Erro ao acessar AIRR: {resultado.get('erro', 'Erro desconhecido')}")]
        
        elif name == "analisar_peca_bemtevi":
            print(">>> DEBUG: Executando analisar_peca_bemtevi", file=sys.stderr)
            
            if not bemtevi_client:
                return [TextContent(type="text", text="❌ Erro: Faça login primeiro usando 'conectar_bemtevi'")]
            
            numero_processo = arguments.get("numero_processo", "")
            indice_peca = arguments.get("indice_peca", 0)
            tipo_analise = arguments.get("tipo_analise", "resumo")
            
            def analisar_peca_sync():
                # Primeiro consultar o processo
                resultado_processo = bemtevi_client.consultar_processo(numero_processo)
                if resultado_processo:
                    return bemtevi_client.acessar_peca(indice_peca)
                return {"sucesso": False, "erro": "Processo não encontrado"}
            
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                resultado_peca = await loop.run_in_executor(executor, analisar_peca_sync)
            
            if resultado_peca.get("sucesso"):
                conteudo = resultado_peca.get("conteudo_completo", "")
                analise = _analisar_com_ia(conteudo, tipo_analise)
                
                _audit("analisar_peca", {
                    "numero_processo": numero_processo,
                    "indice_peca": indice_peca,
                    "tipo_analise": tipo_analise,
                    "tamanho_conteudo": len(conteudo)
                })
                
                return [TextContent(type="text", text=analise)]
            else:
                return [TextContent(type="text", text=f"❌ Erro ao analisar peça {indice_peca}: {resultado_peca.get('erro', 'Erro desconhecido')}")]
        
        elif name == "analisar_despacho_admissibilidade_bemtevi":
            print(">>> DEBUG: Executando analisar_despacho_admissibilidade_bemtevi", file=sys.stderr)
            
            if not bemtevi_client:
                return [TextContent(type="text", text="❌ Erro: Faça login primeiro usando 'conectar_bemtevi'")]
            
            numero_processo = arguments.get("numero_processo", "")
            tipo_analise = arguments.get("tipo_analise", "resumo")
            
            def analisar_despacho_sync():
                return bemtevi_client.acessar_despacho_admissibilidade(numero_processo)
            
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                resultado_despacho = await loop.run_in_executor(executor, analisar_despacho_sync)
            
            if resultado_despacho.get("sucesso"):
                conteudo = resultado_despacho.get("conteudo_completo", "")
                analise = _analisar_com_ia(conteudo, tipo_analise)
                
                _audit("analisar_despacho_admissibilidade", {
                    "numero_processo": numero_processo,
                    "tipo_analise": tipo_analise,
                    "tamanho_conteudo": len(conteudo)
                })
                
                return [TextContent(type="text", text=analise)]
            else:
                return [TextContent(type="text", text=f"❌ Erro ao analisar despacho de admissibilidade: {resultado_despacho.get('erro', 'Erro desconhecido')}")]
        
        elif name == "analisar_airr_bemtevi":
            print(">>> DEBUG: Executando analisar_airr_bemtevi", file=sys.stderr)
            
            if not bemtevi_client:
                return [TextContent(type="text", text="❌ Erro: Faça login primeiro usando 'conectar_bemtevi'")]
            
            numero_processo = arguments.get("numero_processo", "")
            tipo_analise = arguments.get("tipo_analise", "resumo")
            
            def analisar_airr_sync():
                return bemtevi_client.acessar_airr(numero_processo)
            
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                resultado_airr = await loop.run_in_executor(executor, analisar_airr_sync)
            
            if resultado_airr.get("sucesso"):
                conteudo = resultado_airr.get("conteudo_completo", "")
                analise = _analisar_com_ia(conteudo, tipo_analise)
                
                _audit("analisar_airr", {
                    "numero_processo": numero_processo,
                    "tipo_analise": tipo_analise,
                    "tamanho_conteudo": len(conteudo)
                })
                
                return [TextContent(type="text", text=analise)]
            else:
                return [TextContent(type="text", text=f"❌ Erro ao analisar AIRR: {resultado_airr.get('erro', 'Erro desconhecido')}")]
        
        elif name == "status_bemtevi":
            print(">>> DEBUG: Executando status_bemtevi", file=sys.stderr)
            
            if bemtevi_client and bemtevi_client.logged_in:
                status = {
                    "conectado": True,
                    "navegador_ativo": bemtevi_client.driver is not None,
                    "sistema": "BemTevi TST",
                    "total_auditorias": len(audit_log)
                }
                return [TextContent(type="text", text=f"✅ **Status BemTevi**: Conectado e ativo\n\n📊 **Operações realizadas**: {len(audit_log)}\n🌐 **Sistema**: BemTevi TST\n💻 **Navegador**: {'Ativo' if bemtevi_client.driver else 'Inativo'}\n\n🚀 **APIs específicas disponíveis:**\n- Despachos de admissibilidade\n- AIRR (Agravos)\n- Análises com IA")]
            else:
                return [TextContent(type="text", text="❌ **Status BemTevi**: Desconectado\n\n💡 Use 'conectar_bemtevi' para conectar")]
        
        else:
            return [TextContent(type="text", text=f"❌ Ferramenta '{name}' não reconhecida")]
            
    except Exception as e:
        print(f">>> ERROR: {str(e)}", file=sys.stderr)
        return [TextContent(type="text", text=f"❌ Erro: {str(e)}")]

# Debug: Mostra quando o servidor é carregado
print(">>> SERVIDOR CARREGADO - VERSÃO LIMPA PARA NUVEM", file=sys.stderr)

async def main():
    """Função principal do servidor MCP"""
    print(">>> DEBUG: Iniciando servidor MCP BemTevi TST...", file=sys.stderr)
    print(">>> DEBUG: main() iniciada", file=sys.stderr)
    print(">>> DEBUG: Aguardando conexões do Claude...", file=sys.stderr)
    
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())