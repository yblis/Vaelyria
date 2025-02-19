class LDAPTree {
    constructor(containerId, onSelectCallback) {
        this.container = document.getElementById(containerId);
        this.onSelectCallback = onSelectCallback;
        this.data = null;
        this.contextMenu = null;
        this.isOperationInProgress = false;
        this.initContextMenu();
    }

    initContextMenu() {
        this.contextMenu = document.createElement('div');
        this.contextMenu.className = 'ldap-context-menu';
        this.contextMenu.style.display = 'none';
        this.contextMenu.innerHTML = `
            <div class="context-menu-item" data-action="create">
                <i class="fas fa-plus"></i> Créer une OU
            </div>
            <div class="context-menu-item" data-action="rename">
                <i class="fas fa-edit"></i> Renommer
            </div>
            <div class="context-menu-item" data-action="delete">
                <i class="fas fa-trash"></i> Supprimer
            </div>
        `;
        document.body.appendChild(this.contextMenu);

        // Move context menu to the top of the body
        document.body.insertBefore(this.contextMenu, document.body.firstChild);
        
        // Improve click handling
        document.addEventListener('click', (e) => {
            if (!this.contextMenu.contains(e.target)) {
                this.contextMenu.style.display = 'none';
            }
        });
    }

    async loadTree() {
        try {
            const response = await fetch('/api/ldap/ou_tree');
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Erreur de chargement');
            return data;
        } catch (error) {
            console.error('Load error:', error);
            throw error;
        }
    }

    async refreshTree() {
        try {
            this.data = await this.loadTree();
            this.render();
        } catch (error) {
            this.container.innerHTML = '<div class="alert alert-danger">Erreur de chargement</div>';
        }
    }

    async init() {
        await this.refreshTree();
    }

    render() {
        this.container.innerHTML = this.buildTree(this.data);
        this.setupEventListeners();
    }

    buildTree(node) {
        if (!node) return '';
        const hasChildren = node.children && node.children.length > 0;
        return `
            <div class="ldap-node" data-dn="${node.dn}" oncontextmenu="return false;">
                <div class="node-content">
                    ${hasChildren ? 
                        `<span class="toggle-icon">
                            <i class="fas fa-caret-right"></i>
                        </span>` : 
                        '<span class="toggle-icon-placeholder"></span>'
                    }
                    <span class="node-name" title="${node.dn}">
                        <i class="fas ${hasChildren ? 'fa-folder' : 'fa-folder-open'} text-warning"></i>
                        ${node.name}
                    </span>
                </div>
                ${hasChildren ? 
                    `<div class="children" style="display: none;">
                        ${node.children.map(child => this.buildTree(child)).join('')}
                    </div>` : 
                    ''
                }
            </div>
        `;
    }

    setupEventListeners() {
        this.container.querySelectorAll('.ldap-node').forEach(node => {
            node.addEventListener('contextmenu', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const target = e.target.closest('.ldap-node');
                if (!target) return;

                // Position the menu and ensure it stays in viewport
                const rect = this.container.getBoundingClientRect();
                const x = Math.min(e.clientX, window.innerWidth - this.contextMenu.offsetWidth);
                const y = Math.min(e.clientY, window.innerHeight - this.contextMenu.offsetHeight);
                
                this.contextMenu.style.display = 'block';
                this.contextMenu.style.left = x + 'px';
                this.contextMenu.style.top = y + 'px';
                this.contextMenu.setAttribute('data-target-dn', target.dataset.dn);
            });
        });

        this.contextMenu.querySelectorAll('.context-menu-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                if (this.isOperationInProgress) return;
                
                const action = item.dataset.action;
                const targetDn = this.contextMenu.getAttribute('data-target-dn');
                this.handleContextMenuAction(action, targetDn);
                this.contextMenu.style.display = 'none';
            });
        });

        this.container.querySelectorAll('.toggle-icon').forEach(toggle => {
            toggle.addEventListener('click', (e) => {
                e.stopPropagation();
                const node = e.target.closest('.ldap-node');
                const children = node.querySelector('.children');
                const icon = node.querySelector('.toggle-icon i');
                
                if (children) {
                    const isExpanded = children.style.display !== 'none';
                    children.style.display = isExpanded ? 'none' : 'block';
                    icon.className = isExpanded ? 
                        'fas fa-caret-right' : 
                        'fas fa-caret-down';
                }
            });
        });

        this.container.querySelectorAll('.node-name').forEach(nodeName => {
            nodeName.addEventListener('click', (e) => {
                e.stopPropagation();
                this.container.querySelectorAll('.node-name.selected')
                    .forEach(el => el.classList.remove('selected'));
                nodeName.classList.add('selected');

                const dn = e.target.closest('.ldap-node').dataset.dn;
                if (this.onSelectCallback) {
                    this.onSelectCallback(dn);
                }
            });
        });
    }

    async handleContextMenuAction(action, targetDn) {
        if (this.isOperationInProgress) return;
        this.isOperationInProgress = true;

        try {
            switch (action) {
                case 'create': {
                    const newName = prompt('Nom de la nouvelle OU:');
                    if (!newName?.trim()) break;

                    const response = await fetch('/api/ldap/ou/create', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            parent_dn: targetDn,
                            name: newName.trim()
                        })
                    });

                    const data = await response.json();
                    if (!response.ok) throw new Error(data.error || 'Échec de création');

                    await this.refreshTree();
                    this.expandPath(data.dn);
                    break;
                }

                case 'rename': {
                    const newName = prompt('Nouveau nom:');
                    if (!newName?.trim()) break;

                    const response = await fetch(`/api/ldap/ou/${encodeURIComponent(targetDn)}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ new_name: newName.trim() })
                    });

                    const data = await response.json();
                    if (!response.ok) throw new Error(data.error || 'Échec du renommage');

                    await this.refreshTree();
                    break;
                }

                case 'delete': {
                    if (!confirm('Êtes-vous sûr de vouloir supprimer cette OU?')) break;

                    const response = await fetch(`/api/ldap/ou/${encodeURIComponent(targetDn)}`, {
                        method: 'DELETE'
                    });

                    const data = await response.json();
                    if (!response.ok) throw new Error(data.error || 'Échec de la suppression');

                    await this.refreshTree();
                    break;
                }
            }
        } catch (error) {
            console.error('Operation error:', error);
            alert(error.message || 'Une erreur est survenue');
        } finally {
            this.isOperationInProgress = false;
        }
    }

    expandPath(dn) {
        const path = this.findPathToDN(this.data, dn);
        if (!path) return;

        path.forEach(nodeDN => {
            const nodeElement = this.container.querySelector(`[data-dn="${nodeDN}"]`);
            if (nodeElement) {
                const children = nodeElement.querySelector('.children');
                const icon = nodeElement.querySelector('.toggle-icon i');
                if (children) {
                    children.style.display = 'block';
                    icon.className = 'fas fa-caret-down';
                }
            }
        });

        const targetNode = this.container.querySelector(`[data-dn="${dn}"] .node-name`);
        if (targetNode) {
            targetNode.classList.add('selected');
            targetNode.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    findPathToDN(node, targetDN, path = []) {
        if (!node) return null;
        path.push(node.dn);
        if (node.dn === targetDN) return path;
        if (node.children) {
            for (let child of node.children) {
                const result = this.findPathToDN(child, targetDN, [...path]);
                if (result) return result;
            }
        }
        return null;
    }
}
