# Coleção de requisições

Coleção do [Bruno](https://www.usebruno.com/) em `mappacfo/`: abra a pasta no Bruno (Open Collection) e escolha o ambiente `dev`.

Ordem: `csrf` → `login` → `csrf` de novo (o login gira o token) → demais. O Bruno guarda os cookies (`sessionid`, `csrftoken`) entre as requisições; o token CSRF vai no header `X-CSRFToken` pela variável `csrftoken`.

Não salve senhas reais em `environments/`: os arquivos são versionados.
