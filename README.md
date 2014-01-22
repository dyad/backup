backup
======

Ferramenta de backups da Dyad.

Essa ferramenta foi desenvolvida com o objetivo de facilitar o processo de backup das várias bases postgres que temos na empresa.
As necessidades a motivaram:
- Um mesmo script que possa ser utilizado em diferentes servidores.
- Um mesmo script possa ser utilizado nos vários tipos de backup: diários, semanais, mensais etc.
- Colocar a informação sobre as bases em um arquivo de configuração simples, que pode ser alterado por pessoas sem conhecimento de desenvolvimento.
- Usar apenas as ferramentas disponíveis por padrão em ambiente Linux, para que não seja preciso instalar dependências.
- Manter o controle da quantidade de arquivos de backup de cada base que devem permanecer gravados no servidor, para não levar à falta de espaço em disco no servidor e para que não seja necessário intervenção humana para apagar os arquivos mais antigos.

Para atender à essas necessidades, foi desenvolvido um script em Python que lê as informações necessárias de um arquivo de configuração simples, estruturado no formado JSON.
Foi escolhida a linguagem Python basicamente por ela ser mais legível que a linguagem shellscript e porque Python ja vem pré-instalado em praticamente todos os ambientes Linux disponiveis no mercado.

Instalação
======

$ git clone https://github.com/dyad/backup.git

Será criada uma pasta chamada "backup" contendo o script "backup.py".

Utilização
======
Para exibir a ajuda:
$ ./backup.py --help

Para executar um backup
$ ./backup.py --config=config.cfg

Exemplos
======
Exemplo de configuração para backups diários, semanais e mensais:
Arquivos de configuração:

    //backup_diario.cfg
    { 
        "pasta":"/pasta/do/backup/diario",
        "limite_arquivos": 30,
        "servidores":[
            {
                "ip":"127.0.0.1",
                "porta":"5432",
                "usuario":"postgres",
                "senha":"senha-do-postgres",
                "bases":[ "BANCO_1", "BANCO_2" ]
            } 
        ]
    }

    //backup_semanal.cfg
    { 
        "pasta":"/pasta/do/backup/semanal",
        "limite_arquivos": 8,
        "servidores":[
            {
                "ip":"127.0.0.1",
                "porta":"5432",
                "usuario":"postgres",
                "senha":"senha-do-postgres",
                "bases":[ "BANCO_3" ]
            } 
        ]
    }
    
    //backup_mensal.cfg" 
    { 
        "pasta":"/pasta/do/backup/mensal",
        "limite_arquivos": 12,
        "servidores":[
            {
                "ip":"127.0.0.1",
                "porta":"5432",
                "usuario":"postgres",
                "senha":"senha-do-postgres",
                "bases":[ "BANCO_4" ]
            } 
        ]
    }

Para agendar a execução dos backups, criar no CRON do servidor:

    Diario:     backup_dyad.py --config=backup_diario.cfg  
    Semanal:    backup_dyad.py --config=backup_semanal.cfg 
    Mensal:     backup_dyad.py --config=backup_mensal.cfg  

A estrutura de pastas e arquivos de backup ficaria assim: 

/pasta/do/backup/
    |_diario
    |    |_BASE_1
    |    |   |_BASE_1_YYYYMMDD_MD5.bkp 
    |    |   |_BASE_1_YYYYMMDD_MD5.bkp 
    |    |   ... até o limíte de 30 arquivos, informado na propriedade "limite_arquivos" 
    |    |
    |    |_BASE_2
    |        |_BASE_2_YYYYMMDD_MD5.bkp 
    |        |_BASE_2_YYYYMMDD_MD5.bkp 
    |        ... até o limíte de 30 arquivos, informado na propriedade "limite_arquivos" 
    |
    |_semanal
    |    |_BASE_3
    |        |_BASE_3_YYYYMMDD_MD5.bkp 
    |        |_BASE_3_YYYYMMDD_MD5.bkp 
    |        ... até o limíte de 8 arquivos, informado na propriedade "limite_arquivos" 
    |
    |_mensal
        |_BASE_4
            |_BASE_4_YYYYMMDD_MD5.bkp 
            |_BASE_4_YYYYMMDD_MD5.bkp 
            ... até o limíte de 12 arquivos, informado na propriedade "limite_arquivos" 
