import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ThemeProvider extends ChangeNotifier {
  ThemeMode _themeMode = ThemeMode.system;

  ThemeMode get themeMode => _themeMode;

  ThemeProvider() {
    _loadTheme();
  }

  bool get isDarkMode {
    if (_themeMode == ThemeMode.system) {
      return PlatformDispatcher.instance.platformBrightness == Brightness.dark;
    }
    return _themeMode == ThemeMode.dark;
  }

  Future<void> _loadTheme() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final isDark = prefs.getBool('isDarkMode');
      if (isDark == null) {
        _themeMode = ThemeMode.system;
      } else {
        _themeMode = isDark ? ThemeMode.dark : ThemeMode.light;
      }
    } catch (e) {
      debugPrint("Error loading theme: $e");
      _themeMode = ThemeMode.system;
    }
    notifyListeners();
  }

  Future<void> toggleTheme(bool isDark) async {
    _themeMode = isDark ? ThemeMode.dark : ThemeMode.light;
    notifyListeners();
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool('isDarkMode', isDark);
    } catch (e) {
      debugPrint("Error saving theme: $e");
    }
  }
}
