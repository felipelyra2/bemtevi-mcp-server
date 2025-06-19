import json
import logging
import time
import os
import requests
import sys
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

class BemTeviClient:
    def __init__(self):
        self.driver = None
        self.logged_in = False
        self.config = self.carregar_config()
        self.setup_logging()
        self.session = requests.Session()  # Para chamadas de API
        self.logger.info("Cliente BemTevi inicializado")

    def carregar_config(self):
        """Carregar configurações das variáveis de ambiente (adaptado para nuvem)"""
        try:
            # Na nuvem, usar variáveis de ambiente em vez de arquivo JSON
            config = {
                "username": os.getenv("BEMTEVI_USERNAME", ""),
                "password": os.getenv("BEMTEVI_PASSWORD", "")
            }
            
            if not config["username"] or not config["password"]:
                print(">>> ERRO: Variáveis BEMTEVI_USERNAME e BEMTEVI_PASSWORD devem estar configuradas", file=sys.stderr)
            else:
                print(f">>> Config carregado para usuário: {config['username']}", file=sys.stderr)
            
            return config
        except Exception as e:
            print(f">>> Erro ao carregar config: {e}", file=sys.stderr)
            return {"username": "", "password": ""}

    def setup_logging(self):
        """Configurar logging (adaptado para nuvem)"""
        try:
            # Na nuvem, criar logs no diretório atual
            log_dir = os.path.join(os.getcwd(), 'logs')
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            log_file = os.path.join(log_dir, 'bemtevi.log')
            
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s [%(levelname)s] %(message)s',
                handlers=[
                    logging.StreamHandler(sys.stderr),  # Para aparecer nos logs do container
                    logging.FileHandler(log_file, encoding='utf-8'),
                ]
            )
            self.logger = logging.getLogger(__name__)
        except Exception as e:
            # Fallback: só stderr se não conseguir criar arquivo
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s [%(levelname)s] %(message)s',
                handlers=[logging.StreamHandler(sys.stderr)]
            )
            self.logger = logging.getLogger(__name__)
            self.logger.warning(f"Não foi possível criar log file: {e}")

    def iniciar_navegador(self):
        """Inicializar navegador Chrome (adaptado para nuvem)"""
        try:
            self.logger.info("Iniciando navegador Chrome para ambiente cloud...")
            
            chrome_options = Options()
            
            # ===== CONFIGURAÇÕES ESSENCIAIS PARA NUVEM =====
            chrome_options.add_argument("--headless")  # Essencial para nuvem
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-software-rasterizer")
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-backgrounding-occluded-windows")
            chrome_options.add_argument("--disable-renderer-backgrounding")
            chrome_options.add_argument("--disable-features=TranslateUI")
            chrome_options.add_argument("--disable-ipc-flooding-protection")
            
            # Configurações de janela
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--start-maximized")
            
            # User agent para evitar detecção
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            # Performance
            chrome_options.add_argument("--memory-pressure-off")
            chrome_options.add_argument("--max_old_space_size=4096")
            
            # Segurança para ambiente cloud
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--disable-features=VizDisplayCompositor")
            
            # Carregar opções adicionais das variáveis de ambiente
            chrome_options_env = os.getenv("CHROME_OPTIONS", "")
            if chrome_options_env:
                for option in chrome_options_env.split(","):
                    option = option.strip()
                    if option and not any(existing_arg.startswith(option.split('=')[0]) for existing_arg in chrome_options.arguments):
                        chrome_options.add_argument(option)
            
            # Preferências do Chrome
            prefs = {
                "profile.default_content_setting_values": {
                    "notifications": 2,
                    "geolocation": 2,
                    "media_stream": 2,
                },
                "profile.default_content_settings.popups": 0,
                "profile.managed_default_content_settings.images": 2,  # Bloquear imagens para performance
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            # Opções experimentais
            chrome_options.add_experimental_option("useAutomationExtension", False)
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            
            # ===== CONFIGURAÇÃO DO DRIVER =====
            # Remover caminho específico do Windows e usar container/WebDriverManager
            chrome_driver_path = os.getenv("CHROMEDRIVER_PATH")
            
            if chrome_driver_path and os.path.exists(chrome_driver_path):
                self.logger.info(f"Usando ChromeDriver do container: {chrome_driver_path}")
                service = Service(chrome_driver_path)
            else:
                self.logger.info("Usando WebDriver Manager para ChromeDriver...")
                service = Service(ChromeDriverManager().install())
            
            # Timeouts configuráveis
            page_load_timeout = int(os.getenv("PAGE_LOAD_TIMEOUT", "60"))
            selenium_timeout = int(os.getenv("SELENIUM_TIMEOUT", "30"))
            
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Configurar timeouts
            self.driver.set_page_load_timeout(page_load_timeout)
            self.driver.implicitly_wait(selenium_timeout)
            
            # Não fazer maximize_window em headless
            # self.driver.maximize_window()  # Comentado para headless
            
            self.logger.info("Navegador iniciado com sucesso!")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao iniciar navegador: {e}")
            return False

    def fazer_login(self):
        """Fazer login no BemTevi (lógica original mantida)"""
        try:
            if not self.iniciar_navegador():
                return False
            
            self.logger.info("Fazendo login no BemTevi...")
            
            # Navegar para BemTevi
            self.driver.get("https://bemtevi.tst.jus.br/")
            time.sleep(3)
            
            # Preencher usuário
            campo_usuario = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='text']"))
            )
            campo_usuario.clear()
            campo_usuario.send_keys(self.config.get("username", ""))
            self.logger.info("Usuario preenchido")
            
            time.sleep(1)
            
            # Preencher senha
            campo_senha = self.driver.find_element(By.XPATH, "//input[@type='password']")
            campo_senha.clear()
            campo_senha.send_keys(self.config.get("password", ""))
            self.logger.info("Senha preenchida")
            
            time.sleep(2)
            
            # Aguardar spinner desaparecer se existir
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.invisibility_of_element_located((By.ID, "spinner"))
                )
                self.logger.info("Spinner desapareceu")
            except:
                pass
            
            # Clicar no botão de login
            try:
                botao_entrar = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@value='Entrar'] | //input[@id='button-login']"))
                )
                
                try:
                    botao_entrar.click()
                    self.logger.info("Botao de login clicado")
                except:
                    self.driver.execute_script("arguments[0].click();", botao_entrar)
                    self.logger.info("Botao de login clicado via JavaScript")
                
            except Exception as e:
                self.logger.error(f"Erro ao clicar no botão: {e}")
                return False
            
            # Aguardar carregamento após login
            time.sleep(5)
            
            # Verificar se login foi bem-sucedido
            if "5ª Turma" in self.driver.page_source or "bemtevi" in self.driver.current_url.lower():
                self.logged_in = True
                self.logger.info("Login bem-sucedido!")
                
                # Copiar cookies para sessão requests (para APIs)
                self._copiar_cookies_para_session()
                
                return True
            else:
                self.logger.error("Falha no login")
                self.logger.error(f"URL atual: {self.driver.current_url}")
                self.logger.error(f"Página contém: {self.driver.page_source[:500]}...")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro no login: {e}")
            return False

    def _copiar_cookies_para_session(self):
        """Copiar cookies do Selenium para requests.Session (original mantido)"""
        try:
            if self.driver:
                for cookie in self.driver.get_cookies():
                    self.session.cookies.set(cookie['name'], cookie['value'])
                self.logger.info("Cookies copiados para sessão requests")
        except Exception as e:
            self.logger.error(f"Erro ao copiar cookies: {e}")

    def consultar_processo(self, numero_processo):
        """Consultar processo específico via URL direta (original mantido)"""
        try:
            if not self.logged_in:
                self.logger.error("Precisa fazer login primeiro!")
                return None
            
            self.logger.info(f"Consultando processo: {numero_processo}")
            
            # URL direta do processo
            url_processo = f"https://bemtevi.tst.jus.br/report/processo/{numero_processo}"
            self.driver.get(url_processo)
            
            # Aguardar carregamento
            time.sleep(5)
            
            # Verificar se página carregou
            if "processo" in self.driver.page_source.lower() or numero_processo in self.driver.page_source:
                self.logger.info(f"Processo {numero_processo} carregado com sucesso!")
                return self.extrair_informacoes_processo()
            else:
                self.logger.error(f"Processo {numero_processo} não encontrado")
                return None
                
        except Exception as e:
            self.logger.error(f"Erro ao consultar processo: {e}")
            return None

    def extrair_informacoes_processo(self):
        """Extrair informações do processo da página atual (original mantido)"""
        try:
            self.logger.info("Extraindo informações do processo...")
            
            time.sleep(3)
            
            # Extrair título/cabeçalho
            titulo = ""
            try:
                titulo_element = self.driver.find_element(By.XPATH, "//h1 | //h2 | //h3")
                titulo = titulo_element.text.strip()
            except:
                titulo = "Processo TST"
            
            # Extrair informações das peças/tabela
            pecas = []
            try:
                linhas_tabela = self.driver.find_elements(By.XPATH, "//table//tr[td]")
                
                for i, linha in enumerate(linhas_tabela[:20]):
                    try:
                        colunas = linha.find_elements(By.TAG_NAME, "td")
                        
                        if len(colunas) >= 2:
                            tipo_peca = colunas[0].text.strip()
                            data_peca = colunas[1].text.strip() if len(colunas) > 1 else ""
                            
                            # Procurar link na peça
                            href = ""
                            try:
                                link_elemento = linha.find_element(By.TAG_NAME, "a")
                                href = link_elemento.get_attribute("href") or ""
                            except:
                                pass
                            
                            if tipo_peca and len(tipo_peca) > 2:
                                peca = {
                                    "indice": i,
                                    "tipo": tipo_peca,
                                    "data": data_peca,
                                    "href": href,
                                    "tem_link": bool(href)
                                }
                                pecas.append(peca)
                                
                    except Exception as e:
                        continue
                        
            except Exception as e:
                self.logger.error(f"Erro ao extrair peças: {e}")
            
            # Se não encontrou peças na tabela, extrair conteúdo geral
            if not pecas:
                try:
                    body_text = self.driver.find_element(By.TAG_NAME, "body").text
                    if body_text and len(body_text) > 100:
                        peca = {
                            "indice": 0,
                            "tipo": "Conteúdo do processo",
                            "data": datetime.now().strftime("%d/%m/%Y"),
                            "conteudo_completo": body_text,
                            "tem_link": False
                        }
                        pecas.append(peca)
                except:
                    pass
            
            resultado = {
                "titulo": titulo,
                "total_pecas": len(pecas),
                "pecas": pecas,
                "url_atual": self.driver.current_url,
                "timestamp": datetime.now().isoformat()
            }
            
            self.logger.info(f"Extraídas {len(pecas)} informações do processo")
            return resultado
            
        except Exception as e:
            self.logger.error(f"Erro ao extrair informações: {e}")
            return None

    def acessar_despacho_admissibilidade(self, numero_processo):
        """Acessar despacho de admissibilidade via API específica (original mantido)"""
        try:
            self.logger.info(f"Acessando despacho de admissibilidade do processo: {numero_processo}")
            
            if not self.logged_in:
                return {"sucesso": False, "erro": "Precisa fazer login primeiro"}
            
            # URL da API para despachos de admissibilidade
            url_api = f"https://btv-servicos.tst.jus.br/pecas/api/v1/processos/{numero_processo}/decisoes-admissao/todos"
            
            # Fazer requisição para a API
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Referer': 'https://bemtevi.tst.jus.br/',
            }
            
            response = self.session.get(url_api, headers=headers, timeout=30)
            
            if response.status_code == 200:
                try:
                    dados = response.json()
                    
                    if dados and len(dados) > 0:
                        # Processar dados do despacho
                        despacho = dados[0] if isinstance(dados, list) else dados
                        
                        conteudo_texto = ""
                        if isinstance(despacho, dict):
                            # Extrair texto do despacho
                            conteudo_texto = despacho.get('texto', '') or despacho.get('conteudo', '') or despacho.get('decisao', '')
                            if not conteudo_texto:
                                conteudo_texto = json.dumps(despacho, indent=2, ensure_ascii=False)
                        else:
                            conteudo_texto = str(despacho)
                        
                        self.logger.info(f"Despacho de admissibilidade extraído: {len(conteudo_texto)} caracteres")
                        
                        return {
                            "sucesso": True,
                            "tipo": "Despacho de Admissibilidade",
                            "conteudo_completo": conteudo_texto,
                            "dados_estruturados": dados,
                            "tamanho_conteudo": len(conteudo_texto),
                            "url_api": url_api,
                            "metodo_extracao": "API BemTevi - Despachos de Admissão"
                        }
                    else:
                        return {
                            "sucesso": False,
                            "erro": "Nenhum despacho de admissibilidade encontrado"
                        }
                        
                except json.JSONDecodeError as e:
                    # Se não for JSON, tratar como texto
                    conteudo_texto = response.text
                    if len(conteudo_texto) > 50:
                        return {
                            "sucesso": True,
                            "tipo": "Despacho de Admissibilidade",
                            "conteudo_completo": conteudo_texto,
                            "tamanho_conteudo": len(conteudo_texto),
                            "url_api": url_api,
                            "metodo_extracao": "API BemTevi - Resposta texto"
                        }
                    else:
                        return {"sucesso": False, "erro": f"Erro ao processar JSON: {e}"}
            else:
                return {
                    "sucesso": False,
                    "erro": f"Erro na API: HTTP {response.status_code} - {response.text[:200]}"
                }
                
        except Exception as e:
            self.logger.error(f"Erro ao acessar despacho de admissibilidade: {e}")
            return {"sucesso": False, "erro": str(e)}

    def acessar_airr(self, numero_processo):
        """Acessar AIRR (Agravo de Instrumento em Recurso de Revista) via API específica (original mantido)"""
        try:
            self.logger.info(f"Acessando AIRR do processo: {numero_processo}")
            
            if not self.logged_in:
                return {"sucesso": False, "erro": "Precisa fazer login primeiro"}
            
            # URL da API para petições AIRR
            url_api = f"https://btv-servicos.tst.jus.br/pecas/api/v1/processos/{numero_processo}/peticoesAIRR/todos"
            
            # Fazer requisição para a API
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Referer': 'https://bemtevi.tst.jus.br/',
            }
            
            response = self.session.get(url_api, headers=headers, timeout=30)
            
            if response.status_code == 200:
                try:
                    dados = response.json()
                    
                    if dados and len(dados) > 0:
                        # Se há múltiplas petições AIRR, juntar todas
                        conteudo_completo = ""
                        
                        if isinstance(dados, list):
                            for i, airr in enumerate(dados):
                                conteudo_completo += f"\n\n=== AIRR {i+1} ===\n"
                                if isinstance(airr, dict):
                                    texto_airr = airr.get('texto', '') or airr.get('conteudo', '') or airr.get('peticao', '')
                                    if not texto_airr:
                                        texto_airr = json.dumps(airr, indent=2, ensure_ascii=False)
                                    conteudo_completo += texto_airr
                                else:
                                    conteudo_completo += str(airr)
                        else:
                            if isinstance(dados, dict):
                                conteudo_completo = dados.get('texto', '') or dados.get('conteudo', '') or dados.get('peticao', '')
                                if not conteudo_completo:
                                    conteudo_completo = json.dumps(dados, indent=2, ensure_ascii=False)
                            else:
                                conteudo_completo = str(dados)
                        
                        self.logger.info(f"AIRR extraído: {len(conteudo_completo)} caracteres")
                        
                        return {
                            "sucesso": True,
                            "tipo": "AIRR - Agravo de Instrumento em Recurso de Revista",
                            "conteudo_completo": conteudo_completo,
                            "dados_estruturados": dados,
                            "tamanho_conteudo": len(conteudo_completo),
                            "url_api": url_api,
                            "total_airr": len(dados) if isinstance(dados, list) else 1,
                            "metodo_extracao": "API BemTevi - Petições AIRR"
                        }
                    else:
                        return {
                            "sucesso": False,
                            "erro": "Nenhuma petição AIRR encontrada"
                        }
                        
                except json.JSONDecodeError as e:
                    # Se não for JSON, tratar como texto
                    conteudo_texto = response.text
                    if len(conteudo_texto) > 50:
                        return {
                            "sucesso": True,
                            "tipo": "AIRR - Agravo de Instrumento em Recurso de Revista",
                            "conteudo_completo": conteudo_texto,
                            "tamanho_conteudo": len(conteudo_texto),
                            "url_api": url_api,
                            "metodo_extracao": "API BemTevi - Resposta texto"
                        }
                    else:
                        return {"sucesso": False, "erro": f"Erro ao processar JSON: {e}"}
            else:
                return {
                    "sucesso": False,
                    "erro": f"Erro na API: HTTP {response.status_code} - {response.text[:200]}"
                }
                
        except Exception as e:
            self.logger.error(f"Erro ao acessar AIRR: {e}")
            return {"sucesso": False, "erro": str(e)}

    def acessar_peca(self, indice_peca):
        """Acessar uma peça específica e extrair TODO o conteúdo (original mantido)"""
        try:
            self.logger.info(f"Acessando peça índice {indice_peca}")
            
            time.sleep(2)
            
            linhas_tabela = self.driver.find_elements(By.XPATH, "//table//tr[td]")
            
            if indice_peca >= len(linhas_tabela):
                return {
                    "sucesso": False,
                    "erro": f"Índice {indice_peca} inválido. Processo tem {len(linhas_tabela)} peças."
                }
            
            linha_peca = linhas_tabela[indice_peca]
            colunas = linha_peca.find_elements(By.TAG_NAME, "td")
            
            if len(colunas) < 3:
                return {
                    "sucesso": False,
                    "erro": "Estrutura da tabela não reconhecida"
                }
            
            tipo_peca = colunas[0].text.strip()
            data_peca = colunas[1].text.strip()
            coluna_conteudo = colunas[2]
            
            try:
                link_conteudo = coluna_conteudo.find_element(By.TAG_NAME, "a")
                
                self.logger.info(f"Clicando no link da peça: {tipo_peca}")
                
                link_conteudo.click()
                time.sleep(4)
                
                janelas_antes = len(self.driver.window_handles)
                if janelas_antes > 1:
                    self.driver.switch_to.window(self.driver.window_handles[-1])
                    time.sleep(3)
                
                # Estratégias múltiplas para extrair conteúdo
                conteudo_completo = ""
                
                # Estratégia 1: Procurar elementos específicos de documento
                try:
                    elementos_documento = self.driver.find_elements(By.XPATH, 
                        "//div[@class='documento'] | //div[@class='conteudo'] | //div[@class='texto'] | "
                        "//div[contains(@class, 'documento')] | //div[contains(@class, 'conteudo')] | "
                        "//div[contains(@class, 'texto')] | //pre | //div[@id='documento'] | "
                        "//div[@id='conteudo'] | //article | //main"
                    )
                    
                    if elementos_documento:
                        conteudo_partes = []
                        for elem in elementos_documento:
                            texto = elem.text.strip()
                            if texto and len(texto) > 50:
                                conteudo_partes.append(texto)
                        
                        if conteudo_partes:
                            conteudo_completo = "\n\n".join(conteudo_partes)
                
                except Exception as e:
                    self.logger.warning(f"Estratégia 1 falhou: {e}")
                
                # Estratégia 2: Body completo
                if not conteudo_completo or len(conteudo_completo) < 100:
                    try:
                        body_element = self.driver.find_element(By.TAG_NAME, "body")
                        conteudo_completo = body_element.text.strip()
                    except Exception as e:
                        self.logger.warning(f"Estratégia 2 falhou: {e}")
                
                # Voltar para janela original
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
                
                if conteudo_completo and len(conteudo_completo) > 50:
                    return {
                        "sucesso": True,
                        "tipo": tipo_peca,
                        "data": data_peca,
                        "conteudo_completo": conteudo_completo,
                        "tamanho_conteudo": len(conteudo_completo),
                        "url_atual": self.driver.current_url,
                        "metodo_extracao": "Link clicado - conteúdo completo extraído"
                    }
                else:
                    return {
                        "sucesso": False,
                        "erro": "Não foi possível extrair conteúdo significativo da peça"
                    }
                
            except Exception as e:
                # Fallback: extrair da tabela
                try:
                    conteudo_texto = coluna_conteudo.text.strip()
                    if not conteudo_texto:
                        conteudo_texto = f"Peça {tipo_peca} de {data_peca} - Conteúdo não acessível diretamente"
                    
                    return {
                        "sucesso": True,
                        "tipo": tipo_peca,
                        "data": data_peca,
                        "conteudo_completo": conteudo_texto,
                        "url_atual": self.driver.current_url,
                        "metodo_extracao": "Fallback - texto da tabela"
                    }
                except:
                    return {
                        "sucesso": False,
                        "erro": f"Não foi possível acessar o conteúdo da peça {indice_peca}"
                    }
            
        except Exception as e:
            self.logger.error(f"Erro ao acessar peça: {e}")
            return {"sucesso": False, "erro": str(e)}

    def fechar_navegador(self):
        """Fechar navegador"""
        try:
            if self.driver:
                self.driver.quit()
                self.logger.info("Navegador fechado")
        except Exception as e:
            self.logger.error(f"Erro ao fechar navegador: {e}")

    def __del__(self):
        """Cleanup automático"""
        try:
            self.fechar_navegador()
        except:
            pass