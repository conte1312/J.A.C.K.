import 'package:flutter/material.dart';

import 'jack_core_palette.dart';

enum JackCognitiveState {
  idle('In attesa · Nucleo stabile', JackCorePalette.amber),
  listening('Ascolto · Microfono attivo', JackCorePalette.amber),
  understanding(
    'Comprensione · Analisi della richiesta',
    JackCorePalette.amber,
  ),
  retrieving(
    'Recupero conoscenza · Lettura della memoria',
    JackCorePalette.glacier,
  ),
  planning('Pianificazione · Definizione dei passaggi', JackCorePalette.amber),
  executing('Esecuzione strumenti · Moduli in uso', JackCorePalette.glacier),
  responding('Risposta · Composizione in corso', JackCorePalette.amber),
  saving('Salvataggio memoria · Scrittura sul nucleo', JackCorePalette.gold),
  waiting(
    'Conferma richiesta · In attesa del via libera',
    JackCorePalette.amber,
  ),
  error('Errore · Richiesta non completata', JackCorePalette.error);

  const JackCognitiveState(this.label, this.tone);

  final String label;
  final Color tone;
}
