import 'dart:io';

void main() {
  final dir = Directory('lib');
  final regexValues = RegExp(r'\.withValues\(alpha:\s*([^)]+)\)');
  final regexCardTheme = RegExp(r'CardThemeData\(');
  int changedFiles = 0;

  for (final entity in dir.listSync(recursive: true)) {
    if (entity is File && entity.path.endsWith('.dart')) {
      var content = entity.readAsStringSync();
      var newContent = content.replaceAllMapped(regexValues, (match) {
        return '.withOpacity(${match.group(1)})';
      });
      newContent = newContent.replaceAll(regexCardTheme, 'CardTheme(');

      if (content != newContent) {
        entity.writeAsStringSync(newContent);
        changedFiles++;
        print('Updated: ${entity.path}');
      }
    }
  }
  print('Total files updated: $changedFiles');
}
