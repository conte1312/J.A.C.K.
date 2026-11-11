/// Demonstration conversations for the M2 interface.
///
/// These are presentation-only examples. No AI model was queried and no
/// message is persisted. Real conversations arrive with the Conversation
/// Engine (M8).
library;

class DemoChatMessage {
  const DemoChatMessage({
    required this.text,
    required this.fromUser,
    required this.time,
  });

  final String text;
  final bool fromUser;
  final String time;
}

class DemoConversation {
  const DemoConversation({
    required this.id,
    required this.title,
    required this.preview,
    required this.updatedLabel,
    required this.messages,
    required this.contextMemories,
  });

  final String id;
  final String title;
  final String preview;
  final String updatedLabel;
  final List<DemoChatMessage> messages;
  final List<String> contextMemories;
}

const List<DemoConversation> demoConversations = <DemoConversation>[
  DemoConversation(
    id: 'demo-memory-engine',
    title: 'Architettura del Memory Engine',
    preview: 'Categorie, provenienza e knowledge graph…',
    updatedLabel: 'Oggi, 09:41',
    contextMemories: <String>[
      'Progetto J.A.C.K. 2.0',
      'Stack tecnico del progetto',
      'Divisioni del catalogo Agency',
    ],
    messages: <DemoChatMessage>[
      DemoChatMessage(
        text: 'Vorrei definire le basi del Memory Engine: categorie, provenienza e collegamenti tra ricordi.',
        fromUser: true,
        time: '09:32',
      ),
      DemoChatMessage(
        text: 'Partirei da un modello esplicito: ogni ricordo ha una categoria, una fonte, uno stato di verifica e un livello di importanza. I collegamenti diventano entità separate, così il grafo resta interrogabile.',
        fromUser: false,
        time: '09:34',
      ),
      DemoChatMessage(
        text: 'Ha senso separare il database della memoria dagli altri domini?',
        fromUser: true,
        time: '09:37',
      ),
      DemoChatMessage(
        text: 'Sì, se la separazione serve a isolare backup, ciclo di vita e concorrenza. Non va creata per ragioni puramente organizzative: il criterio deve restare tecnico e documentato.',
        fromUser: false,
        time: '09:39',
      ),
      DemoChatMessage(
        text: 'Perfetto. Aggiungerei anche l’approvazione esplicita prima di salvare un ricordo proposto dall’AI.',
        fromUser: true,
        time: '09:41',
      ),
    ],
  ),
  DemoConversation(
    id: 'demo-design-system',
    title: 'Design system: gerarchia e movimento',
    preview: 'Token, contrasto e animazioni discrete…',
    updatedLabel: 'Ieri, 18:20',
    contextMemories: <String>[
      'Identità visiva di J.A.C.K.',
      'Preferenza: risposte concise',
      'Obiettivo della milestone M2',
    ],
    messages: <DemoChatMessage>[
      DemoChatMessage(
        text: 'Il design system deve sembrare premium, non una dashboard amministrativa. Da dove partiamo?',
        fromUser: true,
        time: '18:02',
      ),
      DemoChatMessage(
        text: 'Da tre decisioni: superfici grafite con bordi sottili, un solo accento caldo (ambra/oro) e un accento secondario freddo (cyan) usato con parsimonia. La gerarchia nasce da tipografia e spaziatura, non da ombre pesanti.',
        fromUser: false,
        time: '18:06',
      ),
      DemoChatMessage(
        text: 'E per le animazioni?',
        fromUser: true,
        time: '18:12',
      ),
      DemoChatMessage(
        text: 'Transizioni brevi, curve coerenti e rispetto dell’impostazione di sistema “riduci movimento”. Le animazioni devono spiegare un cambiamento di stato, mai intrattenere.',
        fromUser: false,
        time: '18:14',
      ),
      DemoChatMessage(
        text: 'Aggiungo anche il contrasto: i testi secondari devono restare leggibili sul fondo quasi nero.',
        fromUser: true,
        time: '18:20',
      ),
    ],
  ),
  DemoConversation(
    id: 'demo-planning',
    title: 'Rassegna del venerdì',
    preview: 'Priorità, dipendenze e prossimi passi…',
    updatedLabel: '6 nov',
    contextMemories: <String>[
      'Routine del venerdì',
      'Obiettivo della milestone M2',
      'Team di sviluppo',
    ],
    messages: <DemoChatMessage>[
      DemoChatMessage(
        text:
            'Preparo la rassegna settimanale: quali sono le priorità rimaste?',
        fromUser: true,
        time: '17:10',
      ),
      DemoChatMessage(
        text: 'Tre blocchi: completare le dieci schermate, verificare il layout adattivo e chiudere i test del design system. Le dipendenze critiche sono la navigazione e i componenti condivisi.',
        fromUser: false,
        time: '17:12',
      ),
      DemoChatMessage(
        text: 'Il calendario della prossima settimana è già occupato martedì e giovedì.',
        fromUser: true,
        time: '17:18',
      ),
      DemoChatMessage(
        text: 'Allora concentrerei le attività che richiedono attenzione continua lunedì e mercoledì, lasciando venerdì per la revisione e la documentazione.',
        fromUser: false,
        time: '17:20',
      ),
    ],
  ),
  DemoConversation(
    id: 'demo-agency',
    title: 'Catalogo Agency: divisioni e competenze',
    preview: 'Come organizzare l’anteprima del catalogo…',
    updatedLabel: '4 nov',
    contextMemories: <String>[
      'Divisioni del catalogo Agency',
      'Progetto J.A.C.K. 2.0',
    ],
    messages: <DemoChatMessage>[
      DemoChatMessage(
        text: 'Come mostriamo il catalogo Agency senza far credere che gli agenti siano già operativi?',
        fromUser: true,
        time: '11:05',
      ),
      DemoChatMessage(
        text: 'Separando chiaramente catalogo e runtime: le schede descrivono profili reali del catalogo upstream, mentre lo stato operativo resta “anteprima” finché non esistono provider, strumenti e permessi.',
        fromUser: false,
        time: '11:08',
      ),
      DemoChatMessage(
        text: 'La composizione del team può essere una bozza locale?',
        fromUser: true,
        time: '11:14',
      ),
      DemoChatMessage(
        text: 'Sì, purché sia etichettata come bozza non salvata e non avvii alcuna esecuzione. L’orchestrazione arriverà con una milestone dedicata.',
        fromUser: false,
        time: '11:16',
      ),
    ],
  ),
];
