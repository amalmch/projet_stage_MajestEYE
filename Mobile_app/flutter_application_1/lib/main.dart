import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_application_1/l10n/app_localizations.dart';

import 'core/theme/app_theme.dart';
import 'core/theme/theme_provider.dart';
import 'features/auth/providers/auth_provider.dart';
import 'features/settings/providers/locale_provider.dart';
import 'features/auth/screens/login_screen.dart';
import 'features/complaints/providers/complaint_provider.dart';
import 'features/onboarding/screens/welcome_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  final prefs = await SharedPreferences.getInstance();
  final hasSeenOnboarding = prefs.getBool('onboarding_seen') ?? false;

  runApp(SonedeApp(hasSeenOnboarding: hasSeenOnboarding));
}

class SonedeApp extends StatelessWidget {
  final bool hasSeenOnboarding;

  const SonedeApp({super.key, required this.hasSeenOnboarding});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (context) => AuthProvider()),
        ChangeNotifierProvider(create: (context) => LocaleProvider()),
        ChangeNotifierProvider(create: (context) => ComplaintProvider()),
        ChangeNotifierProvider(create: (context) => ThemeProvider()),
      ],
      child: Consumer2<LocaleProvider, ThemeProvider>(
        builder: (context, localeProvider, themeProvider, child) {
          return MaterialApp(
            debugShowCheckedModeBanner: false,
            title: 'SONEDE Citoyen',
            theme: AppTheme.lightTheme,
            darkTheme: AppTheme.darkTheme,
            themeMode: themeProvider.themeMode,
            locale: localeProvider.locale,
            supportedLocales: const [Locale('fr'), Locale('ar')],
            localizationsDelegates: [
              AppLocalizations.delegate,
              GlobalMaterialLocalizations.delegate,
              GlobalWidgetsLocalizations.delegate,
              GlobalCupertinoLocalizations.delegate,
            ],
            home: hasSeenOnboarding ? const LoginScreen() : const WelcomeScreen(),
          );
        },
      ),
    );
  }
}