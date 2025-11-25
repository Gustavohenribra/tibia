
import sys
import os
import time
import json
import logging

# Setup paths
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'src'))

from src.minimap_reader import MinimapReader
from src.pathfinding import PathfindingSystem
from src.screen_capture_obs import OBSScreenCapture
from src.utils.logger import get_logger

# Mock logger para não precisar de configuração complexa
logging.basicConfig(level=logging.DEBUG)

def test_pathfinding():
    print("Iniciando teste de Pathfinding...")
    
    # Carrega settings reais
    with open('config/bot_settings.json', 'r') as f:
        settings = json.load(f)
        
    # Mock Screen Capture
    screen_capture = OBSScreenCapture()
    
    if not screen_capture.is_available():
        print("ERRO: OBS não disponível.")
        return

    # Init MinimapReader
    minimap_reader = MinimapReader(screen_capture, settings['minimap'])
    
    # Init Pathfinding
    pathfinding_settings = settings['movement'].get('pathfinding', {})
    pf = PathfindingSystem(minimap_reader, pathfinding_settings)
    
    print("\n--- Testando get_next_edge ---")
    edge = pf.get_next_edge()
    
    if edge:
        print(f"SUCESSO: Extremidade encontrada: {edge}")
        print(f"Setor selecionado: {pf.last_sector}")
        print(f"Pesos de setor: {pf.sector_timestamps}")
    else:
        print("FALHA: Nenhuma extremidade retornada!")
        
    print("\n--- Testando get_opposite_direction_edge ---")
    op_edge = pf.get_opposite_direction_edge()
    if op_edge:
        print(f"SUCESSO: Oposto encontrado: {op_edge}")
    else:
        print("FALHA: Oposto não encontrado")

if __name__ == "__main__":
    test_pathfinding()
