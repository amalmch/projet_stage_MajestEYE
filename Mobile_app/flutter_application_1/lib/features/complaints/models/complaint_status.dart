import 'package:flutter/material.dart';

enum ComplaintStatus {
  recue,
  assignee,
  enInspection,
  enReparation,
  resolue,
}

extension ComplaintStatusX on ComplaintStatus {
  String get label {
    switch (this) {
      case ComplaintStatus.recue:
        return 'Reçue';
      case ComplaintStatus.assignee:
        return 'Assignée';
      case ComplaintStatus.enInspection:
        return 'En inspection';
      case ComplaintStatus.enReparation:
        return 'Réparation en cours';
      case ComplaintStatus.resolue:
        return 'Résolue';
    }
  }

  String get description {
    switch (this) {
      case ComplaintStatus.recue:
        return 'Votre réclamation a bien été reçue.';
      case ComplaintStatus.assignee:
        return 'Un technicien a été assigné à votre dossier.';
      case ComplaintStatus.enInspection:
        return 'Une équipe est en cours d\'inspection sur place.';
      case ComplaintStatus.enReparation:
        return 'Les travaux de réparation ont commencé.';
      case ComplaintStatus.resolue:
        return 'Le problème a été résolu. Merci de votre signalement.';
    }
  }

  IconData get icon {
    switch (this) {
      case ComplaintStatus.recue:
        return Icons.inbox_outlined;
      case ComplaintStatus.assignee:
        return Icons.assignment_ind_outlined;
      case ComplaintStatus.enInspection:
        return Icons.search;
      case ComplaintStatus.enReparation:
        return Icons.build_outlined;
      case ComplaintStatus.resolue:
        return Icons.check_circle_outline;
    }
  }

  Color get color {
    switch (this) {
      case ComplaintStatus.recue:
        return Colors.blueGrey;
      case ComplaintStatus.assignee:
        return Colors.indigo;
      case ComplaintStatus.enInspection:
        return Colors.orange;
      case ComplaintStatus.enReparation:
        return Colors.deepOrange;
      case ComplaintStatus.resolue:
        return Colors.green;
    }
  }

  int get stepIndex => ComplaintStatus.values.indexOf(this);
}