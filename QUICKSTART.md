# 🚀 Guia de Início Rápido - 5 Minutos

## 1️⃣ Instalar Dependências (1 minuto)

```bash
pip install -r requirements.txt
```

## 2️⃣ Configurar OBS (2 minutos)

1. Abrir **OBS Studio**
2. Adicionar source: **Window Capture** → Tibia
3. Menu **Tools** → **Start Virtual Camera**
4. Verificar: Deve mostrar "Virtual Camera: Active"

## 3️⃣ Calibrar Regiões (2 minutos)

```bash
py tools/calibrate.py
```

**Para cada região:**
- 🖱️ Clique no canto **superior esquerdo**
- 🖱️ Clique no canto **inferior direito**

Regiões:
- HP Bar (ex: onde mostra "450/650")
- Mana Bar (ex: onde mostra "1200/1850")
- Target HP (opcional - ESC para pular)

## 4️⃣ Ajustar Hotkeys (30 segundos)

Edite `config/skills.json` e ajuste as teclas conforme seu Tibia:

```json
{
  "hotkey": "F1"  ← Mude para a tecla correta
}
```

## 5️⃣ Executar Bot

```bash
py run_bot.py
```

**Pronto!** ✅

---

## ⌨️ Controles

- **Ctrl+C** - Para o bot
- Logs em: `logs/bot_YYYY-MM-DD.log`

---

## 🔧 Se Algo Der Errado

### OBS Virtual Camera não encontrado

```bash
py test_cameras.py
```

Deve mostrar: `[5] OBS Virtual Camera`

Se não aparecer:
- Verificar se Virtual Camera está **ativa** no OBS
- Reiniciar OBS
- Tentar outro índice em `config/bot_settings.json`

### OCR lê valores errados

1. Aumentar fonte do Tibia
2. Aumentar contraste
3. Recalibrar com `py tools/calibrate.py`
4. Ajustar `resize_scale` em `bot_settings.json`

### Bot não aperta teclas

- Tibia deve estar em **foco** (janela ativa)
- Verificar hotkeys em `skills.json`
- Rodar como Administrador se necessário

---

## 📖 Documentação Completa

Veja `README.md` para detalhes completos.

---

**Boa hunt! 🎮**
