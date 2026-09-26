import 'dart:io';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/complaint_provider.dart';
import '../models/complaint_category.dart';
import '../models/complaint_status.dart';
import '../widgets/status_timeline.dart';

class ComplaintDetailScreen extends StatelessWidget {
  final String complaintId;

  const ComplaintDetailScreen({super.key, required this.complaintId});

  String _categoryLabel(String code) {
    final match = complaintCategories.where((c) => c.code == code);
    return match.isNotEmpty ? match.first.label : code;
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<ComplaintProvider>();
    final complaint = provider.getById(complaintId);

    if (complaint == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Réclamation introuvable')),
        body: const Center(child: Text('Cette réclamation n\'existe plus.')),
      );
    }

    final isResolved = complaint.status == ComplaintStatus.resolue;

    return Scaffold(
      appBar: AppBar(title: Text(_categoryLabel(complaint.categorie))),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (complaint.photoPath != null) ...[
              ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: kIsWeb
                    ? Image.network(complaint.photoPath!, height: 180, width: double.infinity, fit: BoxFit.cover)
                    : Image.file(File(complaint.photoPath!), height: 180, width: double.infinity, fit: BoxFit.cover),
              ),
              const SizedBox(height: 16),
            ],
            Text(complaint.texte, style: const TextStyle(fontSize: 15)),
            const SizedBox(height: 4),
            Text(
              'Signalée le ${complaint.dateCreation.day.toString().padLeft(2, '0')}/'
              '${complaint.dateCreation.month.toString().padLeft(2, '0')}/'
              '${complaint.dateCreation.year}',
              style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
            ),
            if (complaint.latitude != null && complaint.longitude != null) ...[
              const SizedBox(height: 4),
              Text(
                'Position : ${complaint.latitude!.toStringAsFixed(4)}, ${complaint.longitude!.toStringAsFixed(4)}',
                style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
              ),
            ],
            const Divider(height: 40),
            const Text(
              'Suivi de la réclamation',
              style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 20),
            StatusTimeline(complaint: complaint),
            ],
        ),
      ),
    );
  }
}