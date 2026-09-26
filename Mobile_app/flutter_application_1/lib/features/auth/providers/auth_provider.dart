import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class AuthProvider extends ChangeNotifier {
  String? _userId;
  String? _userName;
  String? _userEmail;
  String? _phone;
  String? _address;
  String? _governorate;
  String? _delegation;
  String? _profileImageBase64;
  String? _token;

  bool get isAuthenticated => _token != null;
  String? get userId => _userId;
  String? get userName => _userName;
  String? get userEmail => _userEmail;
  String? get phone => _phone;
  String? get address => _address;
  String? get governorate => _governorate;
  String? get delegation => _delegation;
  String? get profileImageBase64 => _profileImageBase64;
  String? get token => _token;

  // Handles emulator (10.0.2.2) vs Web (localhost) mapping
  final String baseUrl = kIsWeb ? 'http://localhost:8080/api' : 'http://10.0.2.2:8080/api';

  AuthProvider() {
    checkLoginStatus();
  }

  Future<void> checkLoginStatus() async {
    final prefs = await SharedPreferences.getInstance();
    _token = prefs.getString('token');
    _userId = prefs.getString('userId');
    _userName = prefs.getString('userName');
    _userEmail = prefs.getString('userEmail');
    _phone = prefs.getString('phone');
    _address = prefs.getString('address');
    _governorate = prefs.getString('governorate');
    _delegation = prefs.getString('delegation');
    _profileImageBase64 = prefs.getString('profileImageBase64');
    notifyListeners();
  }

  Future<void> _saveUserData(Map<String, dynamic> data) async {
    final prefs = await SharedPreferences.getInstance();
    if (data.containsKey('token') && data['token'] != null) {
      _token = data['token'];
      await prefs.setString('token', _token!);
    }
    
    // Auth endpoints usually return {"user": {...}} or similar
    final user = data.containsKey('user') ? data['user'] : data;
    
    _userId = user['id'];
    _userName = user['fullName'];
    _userEmail = user['email'];
    _phone = user['phone'];
    _address = user['address'];
    _governorate = user['governorate'];
    _delegation = user['delegation'];
    _profileImageBase64 = user['profileImageBase64'];

    if (_userId != null) await prefs.setString('userId', _userId!);
    if (_userName != null) await prefs.setString('userName', _userName!);
    if (_userEmail != null) await prefs.setString('userEmail', _userEmail!);
    if (_phone != null) await prefs.setString('phone', _phone!);
    if (_address != null) await prefs.setString('address', _address!);
    if (_governorate != null) await prefs.setString('governorate', _governorate!);
    if (_delegation != null) await prefs.setString('delegation', _delegation!);
    if (_profileImageBase64 != null) await prefs.setString('profileImageBase64', _profileImageBase64!);

    notifyListeners();
  }

  Future<void> login({required String email, required String password}) async {
    final response = await http.post(
      Uri.parse('$baseUrl/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'email': email,
        'password': password,
      }),
    );

    final data = jsonDecode(response.body);
    if (response.statusCode == 200) {
      await _saveUserData(data);
    } else {
      throw Exception(data['error'] ?? 'Login failed');
    }
  }

  Future<void> register({
    required String fullName,
    required String email,
    required String password,
    required String phone,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/auth/register'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'fullName': fullName,
        'email': email,
        'password': password,
        'phone': phone,
      }),
    );

    final data = jsonDecode(response.body);
    if (response.statusCode != 200) {
      throw Exception(data['error'] ?? 'Registration failed');
    }
  }

  Future<void> verifyEmail({required String email, required String code}) async {
    final response = await http.post(
      Uri.parse('$baseUrl/auth/verify-email'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'email': email,
        'code': code,
      }),
    );

    final data = jsonDecode(response.body);
    if (response.statusCode == 200) {
      await _saveUserData(data);
    } else {
      throw Exception(data['error'] ?? 'Verification failed');
    }
  }

  Future<void> forgotPassword(String email) async {
    final response = await http.post(
      Uri.parse('$baseUrl/auth/forgot-password'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email}),
    );

    if (response.statusCode != 200) {
      final data = jsonDecode(response.body);
      throw Exception(data['error'] ?? 'Failed to request reset code');
    }
  }

  Future<void> resetPassword({
    required String email,
    required String code,
    required String newPassword,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/auth/reset-password'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'email': email,
        'code': code,
        'newPassword': newPassword,
      }),
    );

    if (response.statusCode != 200) {
      final data = jsonDecode(response.body);
      throw Exception(data['error'] ?? 'Failed to reset password');
    }
  }

  // --- Profile Endpoints ---

  Future<void> fetchProfile() async {
    if (_token == null) return;
    
    final response = await http.get(
      Uri.parse('$baseUrl/profile'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $_token'
      },
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      await _saveUserData(data);
    }
  }

  Future<void> updateProfile({
    required String fullName,
    String? phone,
    String? address,
    String? governorate,
    String? delegation,
  }) async {
    if (_token == null) throw Exception("Not authenticated");

    final response = await http.put(
      Uri.parse('$baseUrl/profile'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $_token'
      },
      body: jsonEncode({
        'fullName': fullName,
        'phone': phone,
        'address': address,
        'governorate': governorate,
        'delegation': delegation,
      }),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      await _saveUserData(data);
    } else {
      throw Exception('Failed to update profile');
    }
  }

  Future<void> uploadProfileImage(String base64Image) async {
    if (_token == null) throw Exception("Not authenticated");

    final response = await http.post(
      Uri.parse('$baseUrl/profile/image'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $_token'
      },
      body: jsonEncode({'imageBase64': base64Image}),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      await _saveUserData(data);
    } else {
      throw Exception('Failed to upload image');
    }
  }

  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
    _token = null;
    _userId = null;
    _userName = null;
    _userEmail = null;
    _phone = null;
    _address = null;
    _governorate = null;
    _delegation = null;
    _profileImageBase64 = null;
    notifyListeners();
  }
}