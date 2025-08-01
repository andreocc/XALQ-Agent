# GEMINI.md

Este repositório contém práticas, padrões e diretrizes para desenvolvimento e colaboração com assistentes LLM neste projeto.  
Meu nome é André, sou arquiteto de soluções com foco em inovação, sustentabilidade técnica e escalabilidade.  
Trabalho entre ambientes Microsoft Windows e Linux, com ferramentas modernas e automação de ponta a ponta.

---

## 📌 Premissas e Preferências

- Linguagens preferidas: Python, Streamlit, Batch, PowerShell e Bash (para automações); eventualmente PHP ou JS conforme a stack.
- Editor padrão: VSCode com integração à CLI (via `justfile`).
- Controle de versão via `git` — **não** use `rm` ou `mv`; prefira `git rm` e `git mv`.
- Código precisa ser explicável em até 6 meses, sem depender de LLMs para interpretação.
- Estrutura modular: arquivos pequenos, autocontenidos e coesos. Nada de *God objects/files*.
- Output colorido e com logs semânticos. Emojis são aceitáveis quando agregam legibilidade.

---

## 📦 Estrutura Inicial do Projeto

### 📂 Ao iniciar um novo projeto, gere automaticamente os seguintes arquivos:

- `README.md`:  
  Com instruções de uso, instalação, variáveis de ambiente, execução local e deploy.

- `AI_REASONING.md`:  
  Diário técnico contendo o racional de decisões, limitações conhecidas e próximos passos.

- `justfile`:  
  Com as seguintes targets mínimas:
  - `run`: inicia a aplicação localmente
  - `test`: executa todos os testes
  - `list`: mostra os targets disponíveis (`just -l`)

- `.env.dist`:  
  Exemplo das variáveis de ambiente necessárias, com comentários explicativos.  
  Use valores como `foo`, `bar` e `1234` apenas como placeholders.

- `test/`:  
  Pasta padrão com pelo menos um teste inicial (ex: `test_placeholder.py`).

- `.gitignore`:  
  Deve ignorar `.env`, `.cache/`, arquivos `.pyc`, `__pycache__/`, etc.

- `.cache/`:  
  Pasta para armazenamento de dados temporários ou de alto custo computacional.  
  TTL padrão: 1 dia (sobrescrevível via argumento).

---

## 🚀 Aplicação mínima

Crie uma aplicação básica em **Python + Streamlit**, contendo:

- Um formulário simples (ex: entrada de texto e botão de enviar).
- Um log de resposta (pode ser só um `st.write` do input).
- Código dentro de `main.py` ou `app.py`, que possa ser executado com `just run`.

---

## 🤖 Interação com LLM (Gemini)

- Linguagem padrão: Python com `google-adk>=1.0`.
- Use `GOOGLE_GENAI_USE_VERTEXAI=true` em `.env`.
- Defina `GOOGLE_CLOUD_PROJECT` para uso do Vertex AI via SDK.
- Evite usar `SERPAPI_API` salvo exceções justificadas.
- O `AI_REASONING.md` é sua memória. Consulte, atualize e respeite o contexto técnico.
- Sempre leia este `GEMINI.md` antes de atuar no projeto.

---

## 📦 Versionamento e Changelog

- Utilize **versionamento semântico** (`semver`), ex.: `1.2.3`.
- Arquivo `VERSION` com o número atual da versão.
- Mantenha `CHANGELOG.md` sincronizado a cada release.
- Cada release deve gerar imagens Docker:
  - `projeto-x:v1.2.3`
  - `projeto-x:latest`

---

## 🔐 Secrets & Config

- Variáveis sensíveis vão no `.env` (não versionado).
- `.env.dist` documenta todas as variáveis esperadas com exemplos.
- Para produção, considerar uso de serviços como Secret Manager, ou gestão via ambiente da plataforma de deploy.

---

## 🧪 Testes

- Devem ser rápidos, claros e executáveis via `just test`.
- Se um bug for identificado e não houver teste cobrindo, crie um.
- Garantir que `just test` passe antes de qualquer merge para `main`.

---

## 🧠 Boas Práticas de Engenharia

Antes de considerar qualquer tarefa como “concluída”, siga este checklist operacional:

1. **Teste pré-entrega:**  
   - Rode todos os testes automatizados via `just test`.  
   - Execute a aplicação localmente e valide o comportamento esperado.

2. **Diagnóstico orientado a impacto:**  
   Para qualquer bug ou comportamento anômalo:
   - Levante **no máximo 3 causas prováveis**, ranqueadas por **probabilidade**.
   - Para cada causa, proponha **uma solução de no máximo uma linha**.

3. **Código otimizado sempre:**  
   - Elimine gargalos óbvios.  
   - Refatore trechos duplicados ou ilegíveis.  
   - Prefira performance e clareza ao mesmo tempo.

4. **Documentação mínima viável (DMV):**  
   - Atualize `README.md` com novos parâmetros, dependências ou endpoints.
   - Anote decisões técnicas não triviais em `AI_REASONING.md`.

5. **Consistência antes de genialidade:**  
   - Siga o padrão do projeto.
   - Soluções familiares e consistentes são melhores que inovações isoladas.

---

## 🧰 Ferramentas Utilizadas

| Ferramenta     | Uso                          |
|----------------|------------------------------|
| VSCode         | IDE principal                |
| just           | Task runner                  |
| git            | VCS                          |
| Streamlit      | UI interativa para Python    |
| docker         | Build/Deploy                 |
| Vertex AI      | Backend LLM preferido        |
| Google ADK     | Agentes + Tooling LLM        |
| Secret Manager | Gestão de segredos (prod)    |

---

**Lembre-se:** mantenha tudo documentado.  
O que não está documentado, **não existe**.
