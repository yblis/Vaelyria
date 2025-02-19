// Liste des attributs sensibles
const SENSITIVE_ATTRIBUTES = ['ipPhone', 'mobile', 'employeeID'];

// Vérifier si un attribut est sensible
function isSensitive(attribute) {
    return SENSITIVE_ATTRIBUTES.includes(attribute);
}

// Obtenir les attributs sensibles sélectionnés
function getSelectedSensitiveAttributes(selectedAttributes) {
    return selectedAttributes.filter(attr => isSensitive(attr));
}

// Fonction pour demander confirmation pour les attributs sensibles
async function confirmSensitiveExport(selectedAttributes) {
    const sensitiveAttributes = getSelectedSensitiveAttributes(selectedAttributes);
    
    if (sensitiveAttributes.length > 0) {
        const attributesList = sensitiveAttributes.map(attr => {
            switch (attr) {
                case 'ipPhone': return 'Téléphone IP';
                case 'mobile': return 'Téléphone mobile';
                case 'employeeID': return "ID d'employé";
                default: return attr;
            }
        }).join(', ');
        
        return confirm(
            `⚠️ Attention ⚠️\n\n` +
            `Vous avez sélectionné des attributs sensibles :\n` +
            `${attributesList}\n\n` +
            `Voulez-vous continuer l'export ?`
        );
    }
    
    return true;
}
