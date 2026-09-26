import 'dart:io' show Platform;
import 'package:flutter/foundation.dart' show kIsWeb;

/// Configuration centrale de l'URL du backend Flask (sonede_ai/app.py).
///
/// - Sur l'émulateur Android, "localhost" pointe vers l'émulateur lui-même,
///   PAS vers votre PC. Il faut utiliser l'adresse spéciale 10.0.2.2.
/// - Sur le simulateur iOS et sur le web (Chrome), "localhost" fonctionne
///   normalement car ils partagent le réseau du PC.
/// - Sur un téléphone physique (Android ou iOS), ni "localhost" ni
///   "10.0.2.2" ne fonctionnent : il faut mettre l'adresse IP locale de
///   votre PC sur le même Wi-Fi (ex. 192.168.1.23), trouvable avec
///   `ipconfig` (Windows) ou `ifconfig` / `ip a` (Mac/Linux).
class ApiConfig {
  ApiConfig._();

  /// Changez cette valeur si vous testez sur un téléphone physique.
  static const String _physicalDeviceIp = '192.168.1.23'; // <-- à adapter

  static const int port = 5000;

  static String get baseUrl {
    if (kIsWeb) return 'http://localhost:$port';

    if (Platform.isAndroid) {
      // Mettre useEmulator à false si vous testez sur un vrai téléphone.
      const useEmulator = true;
      return useEmulator
          ? 'http://10.0.2.2:$port'
          : 'http://$_physicalDeviceIp:$port';
    }

    if (Platform.isIOS) {
      const useSimulator = true;
      return useSimulator
          ? 'http://localhost:$port'
          : 'http://$_physicalDeviceIp:$port';
    }

    // Windows / macOS / Linux desktop
    return 'http://localhost:$port';
  }
}
