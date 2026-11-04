import 'package:flutter/material.dart';

import '../models/memory.dart';
import '../theme/jack_theme.dart';

class MemoryEditorDialog extends StatefulWidget {
  const MemoryEditorDialog({this.memory, super.key});

  final MemoryRecord? memory;

  @override
  State<MemoryEditorDialog> createState() => _MemoryEditorDialogState();
}

class _MemoryEditorDialogState extends State<MemoryEditorDialog> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _titleController;
  late final TextEditingController _contentController;
  late MemoryCategory _category;

  @override
  void initState() {
    super.initState();
    _titleController = TextEditingController(text: widget.memory?.title ?? '');
    _contentController = TextEditingController(
      text: widget.memory?.content ?? '',
    );
    _category = widget.memory?.category ?? MemoryCategory.note;
  }

  @override
  void dispose() {
    _titleController.dispose();
    _contentController.dispose();
    super.dispose();
  }

  void _submit() {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    final existing = widget.memory;
    Navigator.of(context).pop(
      MemoryDraft(
        title: _titleController.text.trim(),
        content: _contentController.text.trim(),
        category: _category,
        sourceType: existing?.sourceType ?? MemorySourceType.saved,
        source: existing == null ? 'user_entry' : existing.source,
        verification: existing?.verification ?? MemoryVerification.toVerify,
        tags: existing?.tags ?? const [],
        importance: existing?.importance ?? 3,
        excluded: existing?.excluded ?? false,
        conversationId: existing?.conversationId,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final editing = widget.memory != null;
    return AlertDialog(
      backgroundColor: JackPalette.panel,
      titlePadding: const EdgeInsets.fromLTRB(22, 20, 22, 8),
      contentPadding: const EdgeInsets.fromLTRB(22, 4, 22, 4),
      title: Text(
        editing ? 'Modifica ricordo' : 'Nuovo ricordo',
        style: const TextStyle(color: JackPalette.text, fontSize: 17),
      ),
      content: SizedBox(
        width: 450,
        child: SingleChildScrollView(
          child: Form(
            key: _formKey,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextFormField(
                  key: const ValueKey('memory-title-field'),
                  controller: _titleController,
                  autofocus: true,
                  maxLength: 160,
                  decoration: _inputDecoration('Titolo *'),
                  validator: (value) => value == null || value.trim().isEmpty
                      ? 'Inserisci un titolo.'
                      : null,
                ),
                const SizedBox(height: 10),
                TextFormField(
                  key: const ValueKey('memory-content-field'),
                  controller: _contentController,
                  minLines: 5,
                  maxLines: 9,
                  maxLength: 20000,
                  decoration: _inputDecoration('Contenuto *'),
                  validator: (value) => value == null || value.trim().isEmpty
                      ? 'Inserisci il contenuto del ricordo.'
                      : null,
                ),
                const SizedBox(height: 10),
                DropdownButtonFormField<MemoryCategory>(
                  key: const ValueKey('memory-category-field'),
                  initialValue: _category,
                  decoration: _inputDecoration('Categoria *'),
                  dropdownColor: JackPalette.panelRaised,
                  items: [
                    for (final category in MemoryCategory.values)
                      DropdownMenuItem(
                        key: ValueKey(
                          'memory-category-option-${category.apiValue}',
                        ),
                        value: category,
                        child: Text(category.label),
                      ),
                  ],
                  onChanged: (value) {
                    if (value != null) setState(() => _category = value);
                  },
                ),
                const SizedBox(height: 5),
                const Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    'Salvato solo nel database locale di questo Mac.',
                    style: TextStyle(color: JackPalette.dim, fontSize: 9),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
      actionsPadding: const EdgeInsets.fromLTRB(18, 8, 18, 14),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Annulla'),
        ),
        FilledButton(
          key: const ValueKey('save-memory'),
          onPressed: _submit,
          child: Text(editing ? 'Salva modifiche' : 'Salva ricordo'),
        ),
      ],
    );
  }

  InputDecoration _inputDecoration(String label) => InputDecoration(
    labelText: label,
    labelStyle: const TextStyle(color: JackPalette.muted, fontSize: 10),
    alignLabelWithHint: true,
    filled: true,
    fillColor: JackPalette.panelRaised.withValues(alpha: 0.65),
    contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
    enabledBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(10),
      borderSide: const BorderSide(color: JackPalette.borderSoft),
    ),
    focusedBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(10),
      borderSide: const BorderSide(color: JackPalette.amberSoft),
    ),
    errorBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(10),
      borderSide: const BorderSide(color: Color(0xFFFF8A80)),
    ),
    focusedErrorBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(10),
      borderSide: const BorderSide(color: Color(0xFFFF8A80)),
    ),
  );
}
