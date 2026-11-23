# -*- coding: utf-8 -*-
"""
CLI de Execução do Inspetor Headless SharePoint -> Google
Monitor_Esportes - Central Autônoma Suporte Captação
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.sharepoint_inspector_sync import main

if __name__ == "__main__":
    main()
