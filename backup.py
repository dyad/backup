#!/usr/bin/env python2
#! -*- coding:utf8 -*-
import os
import time
import json
import glob
import shutil
import argparse
import textwrap
import subprocess
import logging, logging.handlers
from time import strftime

# TODO
# - Ver como passar os parametros completos para o pg_dump, pq passando só usuario ele pede a senha no terminal. 
#   Se passarmos usuario e senha ele da um erro informando que nao pode passar senha. 
# - Testar o backup de bases em outras maquinas da rede
# - Mostrar no log o tamanho do arquivo gerado
# - Testar a geração direto na pasta de destino, e depois só renomear
# - Testar o envio do arquivo de log principal por email
# - Incluir um código ou descrição no arquivo de configuração, para ser utilizado no log 

############################################################################################################
# Variáveis estáticas globais
# DUMP_CMD = "pg_dump --host=%s --port=%s --username=%s --password=%s %s | gzip > %s"
DUMP_CMD = "pg_dump %s | gzip > %s"
DATE_FORMAT = "%Y%m%d"
ARQUIVO_DE_LOG  = os.path.join(os.path.dirname(os.path.realpath(__file__)),'backup.log') 

############################################################################################################
# Configuracao de parâmetros e help da aplicação
parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description=textwrap.dedent('''\
        Realiza o backup do PostgreSQL com base num arquivo de configuração.
        O arquivo de configuração deve ser um JSON com o seguinte formato:
        {
            "pasta":"/pasta/de/backup", 
            "limite_arquivos": 30, 
            "servidores":[ 
                { 
                    "ip":"127.0.0.1",
                    "porta":"5432",
                    "usuario":"usuario",
                    "senha":"senha",
                    "bases":[ "BASE_1", "BASE_2" ]
                } 
            ] 
        }'''))
parser.add_argument('--config',   required=True,  help='Arquivo JSON de configuração do backup')
parser.add_argument('--loglevel', required=False, help='Nível de log da aplicação')

############################################################################################################
# Configurações de log da aplicação...
# Primeiro apenas cria a variavel global "log". A configuração mesmo foi movida para a função "configura_log".
# Salva o log da aplicação em um arquivo chamado "backup.log" na mesma pasta desse script.
# Ao atingir o tamanho limite de 5MB, o arquivo é salvo com o nome "backup.log.1". 
# Se ja existir um arquivo com esse nome(backup.log.1), esse passará a se chamar "backup.log.2" e o 
# "backup.log" passará a ser o "backup.log.1" e assim por diante até um limíte de 5 arquivos.
log             = logging.getLogger('BACKUP_LOG')
formato_do_log  = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
manipulador     = logging.handlers.RotatingFileHandler( ARQUIVO_DE_LOG, maxBytes=5000000, backupCount=5)
manipulador.setLevel(logging.DEBUG)
manipulador.setFormatter(formato_do_log)
log.addHandler(manipulador)

############################################################################################################
# Funções da aplicação

# def configura_log():
#     formato_do_log  = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
#     manipulador     = logging.handlers.RotatingFileHandler( ARQUIVO_DE_LOG, maxBytes=5000000, backupCount=5)
#     manipulador.setLevel(logging.DEBUG)
#     manipulador.setFormatter(formato_do_log)
#     log.addHandler(manipulador)

def adiciona_notificacao_por_email(mailconfig):
    mailhandler = logging.handlers.SMTPHandler(
        mailhost=mailconfig.get('smtp'),
        fromaddr=mailconfig.get('remetente'),
        toaddrs=mailconfig.get('destinatarios'),
        subject=mailconfig.get('assunto'),
        credentials=(mailconfig.get('usuario'),mailconfig.get('senha')))
    log.addHandler(mailhandler)

def realiza_backup_da_base(ip, porta, usuario, senha, base):
    log.info("====================[ %s:%s/%s ]====================" % (ip, porta, base))
    data    = str(strftime(DATE_FORMAT)) 
    arquivo = "/tmp/%s_%s.sql.pgdump.gz" % (base, data)
    # command = DUMP_CMD % (ip, porta, usuario, senha, base, arquivo)
    command = DUMP_CMD % (base, arquivo)
    log.debug(command)
    subprocess.call(command, shell=True)
    return arquivo

def move_arquivo_para_pasta_destino(arquivo_backup, pasta_destino, base):
    # Calcula o MD5 do arquivo_backup: 
    md5 = subprocess.check_output(["/usr/bin/md5sum", arquivo_backup]).split(" ")[0]
    log.info("MD5 do arquivo %s => %s"%(arquivo_backup, md5))
    if not os.path.isdir(pasta_destino):
        os.mkdir(pasta_destino)
    if not os.path.isdir(os.path.join(pasta_destino,base)):
        os.mkdir(os.path.join(pasta_destino,base))
    data = str(strftime(DATE_FORMAT)) 
    arquivo_destino = os.path.join(pasta_destino, base, "%s_%s_%s.sql.pgdump.gz"%(base,data,md5))
    # Move arquivo_backup para a pasta_destino com o nome "BASE_YYYYMMDD_MD5.bkp.gz"
    log.info("Copiando: %s => %s" % (arquivo_backup, arquivo_destino))
    shutil.move(arquivo_backup, arquivo_destino)

def verifica_limite_arquivos(pasta_destino, base, qtd_limite):
    pasta = os.path.join(pasta_destino, base)
    filtro_de_busca = "%s/%s_*.sql.pgdump.gz"%(pasta, base)
    lista_de_arquivos = glob.glob(filtro_de_busca)
    lista_de_arquivos.sort(reverse=True)
    if len(lista_de_arquivos) is 0:
        log.warning("Atencao! Nenhum arquivo de backup foi encontrado que no formato esperado: %s" % filtro_de_busca)
        return
    aux = 0
    for arquivo in lista_de_arquivos:
        if aux < qtd_limite:
            log.info("Mantendo arquivo:%s" % arquivo)
        else:
            log.info("Apagando arquivo:%s" % arquivo)
            os.unlink(arquivo)
        aux += 1

def realiza_backup_dos_hosts( config ):
    pasta_destino   = config.get("pasta")
    qtd_limite      = config.get("limite_arquivos")
    hosts           = config.get("servidores")
    log.info( "Os arquivos serao gerados sob a pasta '%s', respeitando o limite de %d arquivo(s) por base." % 
        (config.get("pasta"), config.get("limite_arquivos")))
    for host in hosts:
        ip      = host.get("ip")
        porta   = host.get("porta")
        usuario = host.get("usuario")
        senha   = host.get("senha")
        bases   = host.get("bases")
        log.info("Iniciando backup de %d base(s) do host %s " % (len(bases),ip))
        for base in bases:
            try:
                # Faz o backup gerando um arquivo temporário...
                arquivo_backup = realiza_backup_da_base(ip, porta, usuario, senha, base)            
                # Move o arquivo temporario para a pasta de destino com o nome correto...
                move_arquivo_para_pasta_destino(arquivo_backup, pasta_destino, base)
                # Aplica a verificacao do limite de arquivos...
                verifica_limite_arquivos(pasta_destino, base, qtd_limite)
            except Exception, e:
                log.error("Erro ao fazer backup da base %s: %s %s" % (base, type(e), e))

def main( filename ):
    try:
        if not os.path.isfile(filename):
            raise Exception("Arquivo não encontrado: %s" % filename)
        config = json.load(open(filename))
    except Exception as e:
        log.error("Erro ao carregar o arquivo de configuração: %s %s" % (type(e), e))
        return
    # mailconfig = config.get('email')
    # if mailconfig:
    #     adiciona_notificacao_por_email(mailconfig)
    realiza_backup_dos_hosts(config)    

############################################################################################################
# Inicio da execução
# O IF abaixo serve para garantir que o código só será executado quando o script for executado diretamente
# e não quando ele for importado por outro script python, por exemplo. 
# Quando um script é importado por outro script python, a variável global __name__ é diferente de '__main__'

if __name__ == '__main__':
    try:
        # Faz o parse dos argumentos passados...
        args = parser.parse_args()
        
        # configura_log()
        
        # Alteração do nivel de log ...
        numeric_level = logging.DEBUG
        if not args.loglevel == None:
            numeric_level = getattr(logging, args.loglevel.upper(), None)
            if not isinstance(numeric_level, int):
                raise ValueError('Invalid log level: %s' % args.loglevel)
        log.setLevel(numeric_level)

        # Iniciando a aplicacao...
        log.info("Iniciando sessão de backup... ")
        main(args.config)
        log.info("Sessão de backup finalizada.")
    except Exception, e:
        log.error("Erro ao iniciar a aplicação: %s %s" % (type(e), e))

    logging.shutdown()
