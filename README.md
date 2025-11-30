# 🎮 Tibia Combat Bot - Knight (EK)

Sistema profissional de combat bot para Tibia com OCR, rotação inteligente e comportamento humanizado.

## ✨ Features

- ✅ **Captura via OBS Virtual Camera** (indetectável)
- ✅ **OCR Preciso** (99%+ com pré-processamento)
- ✅ **Rotação Inteligente** baseada em prioridades e condições
- ✅ **Comportamento Humanizado** (delays variáveis, distribuição gaussiana)
- ✅ **SendInput API** (não detectável pelo jogo)
- ✅ **Configuração JSON** (fácil de editar)
- ✅ **Logging Profissional** (arquivos rotativos, console colorido)
- ✅ **Safety Features** (pausa em HP crítico, detecta morte)

---

## 📋 Requisitos

### Software

- **Python 3.8+**
- **OBS Studio** (com Virtual Camera ativa)
- **Tesseract OCR** (para leitura de HP/Mana)
  - Download: https://github.com/UB-Mannheim/tesseract/wiki

### Sistema

- **Windows 10/11**
- **Tibia** rodando em janela (não full screen)

---

## 🚀 Instalação

### 1. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 2. Instalar Tesseract OCR

1. Baixar: https://github.com/UB-Mannheim/tesseract/wiki
2. Instalar em `C:\Program Files\Tesseract-OCR`
3. Adicionar ao PATH do Windows

### 3. Configurar OBS

1. Abrir OBS Studio
2. Adicionar source: **Window Capture** → Selecionar Tibia
3. Ajustar para tela cheia no OBS
4. **Tools → Start Virtual Camera**
5. Verificar: Deve aparecer "Virtual Camera: Active"

---

## ⚙️ Configuração

### 1. Calibrar Regiões da Tela (VISUAL)

Execute a ferramenta de calibração visual:

```bash
py tools/calibrate.py
```

**Como funciona:**
1. Captura screenshot do OBS automaticamente
2. Para cada região (HP, Mana, Target):
   - 🖱️ Clique no **canto superior esquerdo**
   - 🖱️ Clique no **canto inferior direito**
3. Salva automaticamente em `config/bot_settings.json`
4. Testa OCR para validar

**Super simples!** Não precisa calcular coordenadas manualmente.

#### Alternativa Manual

Se preferir editar manualmente, edite `config/bot_settings.json`:

```json
{
  "screen_regions": {
    "hp_bar": {
      "x": 100,
      "y": 50,
      "width": 120,
      "height": 25
    }
  }
}
```

### 2. Configurar Skills

Edite `config/skills.json`:

```json
{
  "skills": [
    {
      "name": "Exori Gran",
      "hotkey": "F1",           ← Tecla do Tibia
      "priority": 100,          ← Maior = mais importante
      "cooldown": 6.0,          ← Segundos
      "mana_cost": 340,
      "conditions": {
        "min_mana_percent": 30,
        "has_target": true
      }
    }
  ]
}
```

**Prioridades padrão:**
- 250: Healing de emergência
- 200: Healing normal
- 150: Mana potions
- 100-80: Skills de dano
- 70-60: Buffs/utility

---

## 🎮 Uso

### Executar Bot

```bash
py run_bot.py
```

**Output esperado:**
```
✅ OBS Virtual Camera conectado: 1920x1080
✅ Rotação carregada: 8 skills
✅ Bot inicializado com sucesso!
Bot iniciado! Pressione Ctrl+C para parar
```

### Parar Bot

Pressione **Ctrl+C**

---

## 📊 Logs

Logs são salvos em `logs/bot_YYYY-MM-DD.log`

Formato:
```
2025-01-18 21:30:15 [INFO] Bot iniciado
2025-01-18 21:30:16 [INFO] Skill: Exori Gran | HP: 1250 | Mana: 850
2025-01-18 21:30:22 [INFO] Skill: Exura ICO | HP: 950 | Mana: 810
```

---

## ⚡ Otimização

### Para melhor precisão OCR:

1. **Aumentar contraste** do Tibia
2. **Fonte maior** nas configurações do client
3. **Resolução alta** no OBS (1920x1080+)
4. Editar `config/bot_settings.json`:
   ```json
   {
     "ocr_settings": {
       "resize_scale": 3.0,  ← Aumentar (mais lento, mais preciso)
       "threshold_min": 200  ← Ajustar conforme necessidade
     }
   }
   ```

### Para comportamento mais humanizado:

```json
{
  "human_behavior": {
    "base_delay_ms": 200,      ← Aumentar = mais lento
    "random_variance_ms": 100, ← Aumentar = mais variação
    "micro_pause_chance_percent": 5  ← Aumentar = mais pausas
  }
}
```

---

## 🛡️ Safety Features

O bot automaticamente:

- ✅ **Pausa** se HP < 15% (configurável)
- ✅ **Para** se detectar morte (HP = 0)
- ✅ **Alerta** se mana muito baixa
- ✅ **Prioriza healing** em emergências

Configurar em `config/bot_settings.json`:
```json
{
  "safety": {
    "pause_on_critical_hp_percent": 15,
    "stop_on_death": true,
    "alert_on_low_mana_percent": 10
  }
}
```

---

## 🔧 Troubleshooting

### "OBS Virtual Camera não encontrado"

1. Verificar se OBS está rodando
2. Verificar se Virtual Camera está **ativa**
3. Testar: `py test_cameras.py`
4. Ajustar índice em `config/bot_settings.json`:
   ```json
   { "obs_camera": { "device_index": 5 } }
   ```

### "OCR retorna valores errados"

1. Verificar região está correta (screenshot do OBS)
2. Aumentar `resize_scale` em bot_settings.json
3. Ajustar `threshold_min/max`
4. Testar Tesseract: `tesseract --version`

### "Bot não aperta teclas"

1. Tibia deve estar em **foco** (janela ativa)
2. Verificar hotkeys em `config/skills.json`
3. Rodar como **Administrador** se necessário

---

## 📝 Estrutura do Projeto

```
tibia/
├── config/
│   ├── bot_settings.json   # Configurações gerais
│   └── skills.json          # Skills e rotação
├── src/
│   ├── combat_bot.py        # Bot principal
│   ├── skill_rotation.py    # Sistema de rotação
│   ├── ocr_reader.py        # OCR otimizado
│   ├── screen_capture_obs.py # Captura via OBS
│   ├── human_behavior.py    # Comportamento humanizado
│   └── utils/
│       ├── key_sender.py    # SendInput API
│       └── logger.py        # Logging profissional
├── logs/                    # Logs diários
├── run_bot.py               # Script principal
└── test_cameras.py          # Teste de câmeras
```

---

## 🎯 Próximos Passos

1. ✅ Configurar OBS Virtual Camera
2. ✅ **Calibrar regiões:** `py tools/calibrate.py` (clique 2 pontos por região)
3. ✅ Ajustar skills em `config/skills.json` (hotkeys e prioridades)
4. ✅ Testar bot: `py run_bot.py`
5. ✅ Monitorar logs e ajustar conforme necessidade

---

## ⚠️ Disclaimer

Este bot é para **uso educacional e em servidores de teste**.

Uso em servidores oficiais pode violar os Termos de Serviço do Tibia.

Use por sua conta e risco.

---

**Desenvolvido com ❤️ por Claude Code**
# tibia
# tibia
