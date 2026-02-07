# 🔧 CORREÇÃO - ID da Deputada nas Tabs 2 e 3

## ❌ Problema Encontrado

As Tabs 2 e 3 estavam tentando buscar o `id_deputada` do `st.session_state`, mas no monólito essa variável já existe no escopo global.

**Erro:** "ID da deputada não encontrado. Configure o ID antes de continuar."

---

## ✅ Solução Aplicada

Mudamos as funções `render_tab2()` e `render_tab3()` para **receber o `id_deputada` como parâmetro**.

---

## 📝 Mudanças nos Arquivos

### 1. `tab2_pauta.py`

**ANTES:**
```python
def render_tab2(provider, exibir_detalhes_proposicao_func) -> None:
    # ...
    if run_scan_tab2:
        perfil = provider.get_perfil_deputada() or {}
        id_deputada = st.session_state.get("ID_DEPUTADA") or st.session_state.get("id_deputada")  # ❌ ERRO
```

**DEPOIS:**
```python
def render_tab2(provider, exibir_detalhes_proposicao_func, id_deputada) -> None:  # ✅ Novo parâmetro
    # ...
    if run_scan_tab2:
        perfil = provider.get_perfil_deputada() or {}
        # id_deputada já vem como parâmetro ✅
```

---

### 2. `tab3_palavras_chave.py`

**ANTES:**
```python
def render_tab3(provider) -> None:
    # ...
    if run_scan_tab3:
        perfil = provider.get_perfil_deputada() or {}
        id_deputada = st.session_state.get("ID_DEPUTADA") or st.session_state.get("id_deputada")  # ❌ ERRO
```

**DEPOIS:**
```python
def render_tab3(provider, id_deputada) -> None:  # ✅ Novo parâmetro
    # ...
    if run_scan_tab3:
        perfil = provider.get_perfil_deputada() or {}
        # id_deputada já vem como parâmetro ✅
```

---

## 🔧 Como Usar no monitor_sistema_jz.py

### Tab 2 (Autoria & Relatoria)

```python
with tab2:
    _set_aba_atual(2)
    from modules.tabs.tab2_pauta import render_tab2
    render_tab2(provider, exibir_detalhes_proposicao, id_deputada)  # ✅ Passa id_deputada
```

### Tab 3 (Palavras-chave)

```python
with tab3:
    _set_aba_atual(3)
    from modules.tabs.tab3_palavras_chave import render_tab3
    render_tab3(provider, id_deputada)  # ✅ Passa id_deputada
```

---

## ⚠️ IMPORTANTE

A variável `id_deputada` **já existe** no `monitor_sistema_jz.py`, então basta passar como parâmetro!

No monólito, ela é definida perto do início do arquivo, algo como:

```python
# Próximo ao início do arquivo monitor_sistema_jz.py
id_deputada = 220559  # ou vem de alguma config
```

Então é só passar essa variável para as funções render!

---

## ✅ Arquivos Corrigidos Entregues

1. ✅ `tab2_pauta.py` - Agora recebe `id_deputada` como parâmetro
2. ✅ `tab3_palavras_chave.py` - Agora recebe `id_deputada` como parâmetro

---

## 🎯 Teste Rápido

Depois de atualizar o código, teste:

```bash
streamlit run monitor_sistema_jz.py
```

1. Abrir Tab 2
2. Selecionar período
3. Clicar "Carregar pauta"
4. ✅ Deve funcionar sem erro de ID!

---

*Correção aplicada em: 07/02/2026*
