import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class LocaleProvider extends ChangeNotifier {
  Locale _locale = const Locale('fr'); // Default to French

  Locale get locale => _locale;

  LocaleProvider() {
    _loadLocale();
  }

  Future<void> _loadLocale() async {
    final prefs = await SharedPreferences.getInstance();
    final langCode = prefs.getString('languageCode');
    if (langCode != null) {
      _locale = Locale(langCode);
      notifyListeners();
    }
  }

  Future<void> setLocale(Locale newLocale) async {
    if (_locale != newLocale) {
      _locale = newLocale;
      notifyListeners();
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('languageCode', newLocale.languageCode);
    }
  }
}