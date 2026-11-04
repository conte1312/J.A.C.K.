import 'dart:async';

import 'package:flutter/material.dart';

import '../models/memory.dart';
import '../services/local_api_client.dart';
import '../services/memory_api_service.dart';
import '../theme/jack_theme.dart';
import '../widgets/jack_primitives.dart';
import '../widgets/memory_editor_dialog.dart';
import '../widgets/memory_entry_card.dart';

class MemoryScreen extends StatefulWidget {
  const MemoryScreen({this.repository, super.key});

  final MemoryRepository? repository;

  @override
  State<MemoryScreen> createState() => _MemoryScreenState();
}

class _MemoryScreenState extends State<MemoryScreen> {
  late final MemoryRepository _repository;
  final _searchController = TextEditingController();
  final List<MemoryRecord> _memories = [];
  Timer? _searchDebounce;
  MemoryCategory? _category;
  String _query = '';
  String? _errorMessage;
  bool _loading = true;
  bool _saving = false;
  bool _offline = false;
  bool _hasLoaded = false;
  int _requestNumber = 0;

  @override
  void initState() {
    super.initState();
    _repository = widget.repository ?? MemoryApiService();
    unawaited(_loadMemories());
  }

  @override
  void dispose() {
    _searchDebounce?.cancel();
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadMemories({bool showLoading = true}) async {
    final requestNumber = ++_requestNumber;
    if (mounted) {
      setState(() {
        if (showLoading) _loading = true;
        _errorMessage = null;
      });
    }

    try {
      final results = await _repository.list(
        query: _query,
        category: _category,
      );
      if (!mounted || requestNumber != _requestNumber) return;
      setState(() {
        _memories
          ..clear()
          ..addAll(results);
        _loading = false;
        _hasLoaded = true;
        _offline = false;
        _errorMessage = null;
      });
    } on Exception catch (error) {
      if (!mounted || requestNumber != _requestNumber) return;
      setState(() {
        _loading = false;
        _offline = error is LocalApiException && error.statusCode == null;
        _errorMessage = _messageFor(error);
      });
    }
  }

  String _messageFor(Object error) {
    if (error is LocalApiException) return error.message;
    return 'Non riesco a leggere le memorie dal backend locale.';
  }

  void _onSearchChanged(String value) {
    setState(() => _query = value);
    _searchDebounce?.cancel();
    _searchDebounce = Timer(
      const Duration(milliseconds: 300),
      () => unawaited(_loadMemories()),
    );
  }

  void _onCategoryChanged(MemoryCategory? value) {
    setState(() => _category = value);
    unawaited(_loadMemories());
  }

  Future<void> _openEditor({MemoryRecord? memory}) async {
    final draft = await showDialog<MemoryDraft>(
      context: context,
      builder: (context) => MemoryEditorDialog(memory: memory),
    );
    if (draft == null || !mounted) return;
    await _saveMemory(draft, existing: memory);
  }

  Future<void> _saveMemory(MemoryDraft draft, {MemoryRecord? existing}) async {
    if (_saving || !_hasLoaded || _offline) return;
    setState(() {
      _saving = true;
      _errorMessage = null;
    });

    try {
      final saved = existing == null
          ? await _repository.create(draft)
          : await _repository.update(existing.id, draft);
      if (!mounted) return;
      setState(() {
        _mergeSavedMemory(saved);
        _saving = false;
        _offline = false;
      });
      _showMessage(
        existing == null
            ? 'Ricordo salvato nel database locale di questo Mac.'
            : 'Ricordo aggiornato nel database locale.',
      );
      await _loadMemories(showLoading: false);
    } on Exception catch (error) {
      if (!mounted) return;
      setState(() {
        _saving = false;
        _offline = error is LocalApiException && error.statusCode == null;
        _errorMessage = _messageFor(error);
      });
      _showMessage(_messageFor(error), isError: true);
    }
  }

  Future<void> _confirmDelete(MemoryRecord memory) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: JackPalette.panel,
        title: const Text(
          'Eliminare il ricordo?',
          style: TextStyle(color: JackPalette.text),
        ),
        content: Text(
          '“${memory.title}” verrà eliminato dal database locale di questo Mac.',
          style: const TextStyle(color: JackPalette.muted, height: 1.5),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Annulla'),
          ),
          FilledButton(
            key: const ValueKey('confirm-delete-memory'),
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Elimina'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted || _offline || !_hasLoaded) return;

    setState(() {
      _saving = true;
      _errorMessage = null;
    });
    try {
      await _repository.delete(memory.id);
      if (!mounted) return;
      setState(() {
        _memories.removeWhere((item) => item.id == memory.id);
        _saving = false;
      });
      _showMessage('Ricordo eliminato dal database locale.');
      await _loadMemories(showLoading: false);
    } on Exception catch (error) {
      if (!mounted) return;
      setState(() {
        _saving = false;
        _offline = error is LocalApiException && error.statusCode == null;
        _errorMessage = _messageFor(error);
      });
      _showMessage(_messageFor(error), isError: true);
    }
  }

  void _mergeSavedMemory(MemoryRecord saved) {
    _memories.removeWhere((item) => item.id == saved.id);
    if (_matchesCurrentFilters(saved)) _memories.add(saved);
    _sortMemories();
  }

  bool _matchesCurrentFilters(MemoryRecord memory) {
    if (_category != null && memory.category != _category) return false;
    final query = _query.trim().toLowerCase();
    if (query.isEmpty) return true;
    return memory.title.toLowerCase().contains(query) ||
        memory.content.toLowerCase().contains(query);
  }

  void _sortMemories() {
    _memories.sort((a, b) => b.updatedAt.compareTo(a.updatedAt));
  }

  void _showMessage(String message, {bool isError = false}) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Text(message),
          backgroundColor: isError ? const Color(0xFF572D2B) : null,
          duration: const Duration(seconds: 3),
        ),
      );
  }

  bool get _canWrite => _hasLoaded && !_offline && !_loading && !_saving;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: JackPalette.panel,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: JackPalette.border),
      ),
      clipBehavior: Clip.antiAlias,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(22, 20, 22, 18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _Header(
              loading: _loading,
              offline: _offline,
              hasError: _errorMessage != null,
              canWrite: _canWrite,
              onAdd: () => unawaited(_openEditor()),
            ),
            const SizedBox(height: 14),
            const _LocalStorageNotice(),
            const SizedBox(height: 13),
            _SearchAndFilter(
              controller: _searchController,
              query: _query,
              category: _category,
              onSearchChanged: _onSearchChanged,
              onCategoryChanged: _onCategoryChanged,
            ),
            if (_errorMessage != null && _hasLoaded) ...[
              const SizedBox(height: 10),
              _OfflineBanner(
                message: _errorMessage!,
                offline: _offline,
                onRetry: () => unawaited(_loadMemories()),
              ),
            ],
            const SizedBox(height: 12),
            Expanded(child: _buildResults()),
          ],
        ),
      ),
    );
  }

  Widget _buildResults() {
    if (_loading && !_hasLoaded) {
      return const Center(
        child: CircularProgressIndicator(
          strokeWidth: 2,
          color: JackPalette.amber,
        ),
      );
    }
    if (!_hasLoaded && _errorMessage != null) {
      return _UnavailableState(
        message: _errorMessage!,
        offline: _offline,
        onRetry: () => unawaited(_loadMemories()),
      );
    }
    if (_memories.isEmpty) {
      final hasFilter = _query.trim().isNotEmpty || _category != null;
      return _EmptyState(
        filtered: hasFilter,
        canWrite: _canWrite,
        onAdd: () => unawaited(_openEditor()),
        onClear: () {
          _searchController.clear();
          setState(() {
            _query = '';
            _category = null;
          });
          unawaited(_loadMemories());
        },
      );
    }

    return Stack(
      children: [
        ListView.separated(
          key: const ValueKey('memory-list'),
          padding: const EdgeInsets.only(bottom: 8),
          itemCount: _memories.length,
          separatorBuilder: (context, index) => const SizedBox(height: 9),
          itemBuilder: (context, index) {
            final memory = _memories[index];
            return MemoryEntryCard(
              memory: memory,
              enabled: _canWrite,
              onEdit: () => unawaited(_openEditor(memory: memory)),
              onDelete: () => unawaited(_confirmDelete(memory)),
            );
          },
        ),
        if (_loading || _saving)
          const Positioned(
            top: 0,
            left: 0,
            right: 0,
            child: LinearProgressIndicator(
              minHeight: 2,
              color: JackPalette.amber,
              backgroundColor: JackPalette.border,
            ),
          ),
      ],
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({
    required this.loading,
    required this.offline,
    required this.hasError,
    required this.canWrite,
    required this.onAdd,
  });

  final bool loading;
  final bool offline;
  final bool hasError;
  final bool canWrite;
  final VoidCallback onAdd;

  @override
  Widget build(BuildContext context) {
    final status = loading
        ? 'Verifica memoria locale'
        : offline
        ? 'Backend memoria · offline'
        : hasError
        ? 'Servizio memoria · errore'
        : 'SQLite locale · disponibile';
    final color = loading
        ? JackPalette.amber
        : offline || hasError
        ? JackPalette.dim
        : JackPalette.green;

    return Row(
      children: [
        Container(
          width: 38,
          height: 38,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: JackPalette.cyan.withValues(alpha: 0.07),
            border: Border.all(color: JackPalette.cyan.withValues(alpha: 0.2)),
          ),
          child: const Icon(
            Icons.bookmarks_outlined,
            color: JackPalette.cyan,
            size: 18,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SectionEyebrow('Memoria locale'),
              const SizedBox(height: 4),
              const Text(
                'Memoria',
                style: TextStyle(
                  color: JackPalette.text,
                  fontSize: 24,
                  fontWeight: FontWeight.w300,
                  letterSpacing: -0.25,
                ),
              ),
              const SizedBox(height: 4),
              Row(
                children: [
                  StatusDot(color: color, size: 5),
                  const SizedBox(width: 6),
                  Flexible(
                    child: Text(
                      status,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(color: color, fontSize: 8),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(width: 10),
        OutlinedButton.icon(
          key: const ValueKey('add-memory'),
          onPressed: canWrite ? onAdd : null,
          icon: const Icon(Icons.add_rounded, size: 15),
          label: const Text('Nuovo ricordo'),
          style: OutlinedButton.styleFrom(
            foregroundColor: JackPalette.text,
            disabledForegroundColor: JackPalette.dim,
            side: const BorderSide(color: JackPalette.border),
            minimumSize: const Size(0, 37),
            padding: const EdgeInsets.symmetric(horizontal: 12),
            textStyle: const TextStyle(fontSize: 10),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(11),
            ),
          ),
        ),
      ],
    );
  }
}

class _LocalStorageNotice extends StatelessWidget {
  const _LocalStorageNotice();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: JackPalette.cyan.withValues(alpha: 0.045),
        borderRadius: BorderRadius.circular(11),
        border: Border.all(color: JackPalette.cyan.withValues(alpha: 0.14)),
      ),
      child: const Row(
        children: [
          Icon(Icons.storage_outlined, color: JackPalette.cyan, size: 14),
          SizedBox(width: 8),
          Expanded(
            child: Text(
              'I ricordi che inserisci vengono salvati localmente su questo Mac. Nessuna sincronizzazione cloud.',
              style: TextStyle(
                color: JackPalette.muted,
                fontSize: 9,
                height: 1.4,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _SearchAndFilter extends StatelessWidget {
  const _SearchAndFilter({
    required this.controller,
    required this.query,
    required this.category,
    required this.onSearchChanged,
    required this.onCategoryChanged,
  });

  final TextEditingController controller;
  final String query;
  final MemoryCategory? category;
  final ValueChanged<String> onSearchChanged;
  final ValueChanged<MemoryCategory?> onCategoryChanged;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final search = TextField(
          key: const ValueKey('memory-search'),
          controller: controller,
          onChanged: onSearchChanged,
          style: const TextStyle(color: JackPalette.text, fontSize: 10),
          decoration: InputDecoration(
            hintText: 'Cerca titolo o contenuto…',
            hintStyle: const TextStyle(color: JackPalette.dim, fontSize: 10),
            prefixIcon: const Icon(
              Icons.search_rounded,
              color: JackPalette.dim,
              size: 16,
            ),
            suffixIcon: query.isEmpty
                ? null
                : IconButton(
                    tooltip: 'Cancella ricerca',
                    onPressed: () {
                      controller.clear();
                      onSearchChanged('');
                    },
                    icon: const Icon(Icons.close_rounded, size: 14),
                  ),
            filled: true,
            fillColor: JackPalette.panelRaised.withValues(alpha: 0.55),
            contentPadding: const EdgeInsets.symmetric(vertical: 11),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(11),
              borderSide: const BorderSide(color: JackPalette.borderSoft),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(11),
              borderSide: const BorderSide(color: JackPalette.amberSoft),
            ),
          ),
        );
        final categoryFilter = _CategoryFilter(
          category: category,
          onChanged: onCategoryChanged,
        );

        if (constraints.maxWidth < 620) {
          return Column(
            children: [search, const SizedBox(height: 8), categoryFilter],
          );
        }
        return Row(
          children: [
            Expanded(child: search),
            const SizedBox(width: 10),
            SizedBox(width: 205, child: categoryFilter),
          ],
        );
      },
    );
  }
}

class _CategoryFilter extends StatelessWidget {
  const _CategoryFilter({required this.category, required this.onChanged});

  final MemoryCategory? category;
  final ValueChanged<MemoryCategory?> onChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 42,
      padding: const EdgeInsets.symmetric(horizontal: 10),
      decoration: BoxDecoration(
        color: JackPalette.panelRaised.withValues(alpha: 0.55),
        borderRadius: BorderRadius.circular(11),
        border: Border.all(color: JackPalette.borderSoft),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<MemoryCategory?>(
          key: const ValueKey('memory-category-filter'),
          value: category,
          isExpanded: true,
          dropdownColor: JackPalette.panelRaised,
          icon: const Icon(
            Icons.keyboard_arrow_down_rounded,
            color: JackPalette.muted,
            size: 17,
          ),
          style: const TextStyle(color: JackPalette.muted, fontSize: 9),
          items: [
            const DropdownMenuItem<MemoryCategory?>(
              value: null,
              child: Text('Tutte le categorie'),
            ),
            for (final item in MemoryCategory.values)
              DropdownMenuItem<MemoryCategory?>(
                key: ValueKey('memory-filter-option-${item.apiValue}'),
                value: item,
                child: Text(item.label),
              ),
          ],
          onChanged: onChanged,
        ),
      ),
    );
  }
}

class _OfflineBanner extends StatelessWidget {
  const _OfflineBanner({
    required this.message,
    required this.offline,
    required this.onRetry,
  });

  final String message;
  final bool offline;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(11, 8, 7, 8),
      decoration: BoxDecoration(
        color: JackPalette.amber.withValues(alpha: 0.055),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: JackPalette.amber.withValues(alpha: 0.16)),
      ),
      child: Row(
        children: [
          Icon(
            offline ? Icons.cloud_off_rounded : Icons.warning_amber_rounded,
            size: 14,
            color: JackPalette.amber,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              offline && message.isNotEmpty
                  ? '$message Ultimo elenco caricato mantenuto sullo schermo; le modifiche non sono salvate.'
                  : message,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                color: JackPalette.muted,
                fontSize: 9,
                height: 1.4,
              ),
            ),
          ),
          IconButton(
            key: const ValueKey('retry-memory-load'),
            tooltip: 'Riprova',
            onPressed: onRetry,
            visualDensity: VisualDensity.compact,
            iconSize: 15,
            color: JackPalette.muted,
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
    );
  }
}

class _UnavailableState extends StatelessWidget {
  const _UnavailableState({
    required this.message,
    required this.offline,
    required this.onRetry,
  });

  final String message;
  final bool offline;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(18),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              offline ? Icons.cloud_off_rounded : Icons.warning_amber_rounded,
              color: JackPalette.amber,
              size: 31,
            ),
            const SizedBox(height: 12),
            Text(
              offline
                  ? 'Backend locale offline'
                  : 'Memoria locale non disponibile',
              textAlign: TextAlign.center,
              style: const TextStyle(color: JackPalette.text, fontSize: 15),
            ),
            const SizedBox(height: 7),
            Text(
              message,
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: JackPalette.muted,
                fontSize: 10,
                height: 1.5,
              ),
            ),
            const SizedBox(height: 15),
            OutlinedButton.icon(
              key: const ValueKey('retry-memory-load'),
              onPressed: onRetry,
              icon: const Icon(Icons.refresh_rounded, size: 14),
              label: const Text('Riprova'),
            ),
          ],
        ),
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({
    required this.filtered,
    required this.canWrite,
    required this.onAdd,
    required this.onClear,
  });

  final bool filtered;
  final bool canWrite;
  final VoidCallback onAdd;
  final VoidCallback onClear;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            filtered ? Icons.search_off_rounded : Icons.bookmark_border_rounded,
            color: JackPalette.dim,
            size: 31,
          ),
          const SizedBox(height: 11),
          Text(
            filtered
                ? 'Nessun ricordo corrisponde ai filtri.'
                : 'Ancora nessun ricordo salvato.',
            textAlign: TextAlign.center,
            style: const TextStyle(color: JackPalette.text, fontSize: 13),
          ),
          const SizedBox(height: 6),
          Text(
            filtered
                ? 'Prova un’altra ricerca o categoria.'
                : 'I ricordi verranno salvati solo quando li inserisci tu.',
            textAlign: TextAlign.center,
            style: const TextStyle(color: JackPalette.dim, fontSize: 9),
          ),
          const SizedBox(height: 14),
          if (filtered)
            TextButton(
              key: const ValueKey('clear-memory-filters'),
              onPressed: onClear,
              child: const Text('Cancella filtri'),
            )
          else
            OutlinedButton.icon(
              key: const ValueKey('add-first-memory'),
              onPressed: canWrite ? onAdd : null,
              icon: const Icon(Icons.add_rounded, size: 14),
              label: const Text('Aggiungi un ricordo'),
            ),
        ],
      ),
    );
  }
}
