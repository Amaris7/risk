"""Gemensamt för Python-testerna: gör skript/ importerbart."""
import os
import sys

ROT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROT, "skript"))
