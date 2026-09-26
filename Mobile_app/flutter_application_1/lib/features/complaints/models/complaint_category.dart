class ComplaintCategory {
  final String code;
  final String label;

  const ComplaintCategory({required this.code, required this.label});
}

const List<ComplaintCategory> complaintCategories = [
  ComplaintCategory(code: 'coupure_non_signalee', label: 'Coupure d\'eau'),
  ComplaintCategory(code: 'qualite_eau', label: 'Qualité de l\'eau'),
  ComplaintCategory(code: 'fuite_visible', label: 'Fuite visible'),
  ComplaintCategory(code: 'pression_faible', label: 'Pression insuffisante'),
  ComplaintCategory(code: 'facturation', label: 'Litige de facturation'),

];