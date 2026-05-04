const { createApp } = Vue;

createApp({
    delimiters: ['[[', ']]'],
    data() {
        return {
            accounts: [],
            total: 0,
            page: 1,
            stats: { total:0, available:0, used_today:0, total_capacity:0, remaining_today:0 },
            unifiedPassword: '',
            currentAccount: null,
            noAvailable: false,
            filters: { group: 'all', search: '' },
            groups: [],
            darkMode: false
        }
    },
    mounted() {
        this.initTheme();
        this.loadGroups();
        this.loadStats();
        this.loadAccounts();
    },
    methods: {
        initTheme() {
            const saved = localStorage.getItem('darkMode') === 'true';
            const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            if (saved) {
                this.darkMode = true;
                document.documentElement.classList.add('dark-mode');
            } else if (systemDark && localStorage.getItem('darkMode') === null) {
                this.darkMode = true;
                document.documentElement.classList.add('dark-mode');
            }
        },
        toggleDarkMode() {
            this.darkMode = !this.darkMode;
            if (this.darkMode) {
                document.documentElement.classList.add('dark-mode');
            } else {
                document.documentElement.classList.remove('dark-mode');
            }
            localStorage.setItem('darkMode', this.darkMode);
        },
        async loadGroups() {
            const res = await axios.get('/api/groups');
            this.groups = res.data;
        },
        async loadStats() {
            const res = await axios.get('/api/stats');
            this.stats = res.data;
            this.unifiedPassword = res.data.unified_password;
        },
        async loadAccounts() {
            const params = {
                page: this.page,
                per_page: 50,
                group: this.filters.group,
                search: this.filters.search
            };
            const res = await axios.get('/api/accounts', { params });
            this.accounts = res.data.items;
            this.total = res.data.total;
        },
        async getAvailableAccount() {
            const params = { only_available: true, per_page: 1 };
            if (this.filters.group !== 'all') params.group = this.filters.group;
            if (this.filters.search) params.search = this.filters.search;
            const res = await axios.get('/api/accounts', { params });
            if (res.data.items.length === 0) {
                this.noAvailable = true;
                this.currentAccount = null;
            } else {
                this.noAvailable = false;
                this.currentAccount = res.data.items[0];
            }
        },
        async useOne(accountId) {
            try {
                const res = await axios.post(`/api/accounts/${accountId}/use`);
                this.$message.success(res.data.message);
                await this.loadStats();
                await this.loadAccounts();
                if (this.currentAccount && this.currentAccount.id === accountId) {
                    this.currentAccount.remaining = res.data.remaining;
                    if (res.data.remaining === 0 && res.data.next_id) {
                        const nextRes = await axios.get('/api/accounts', { params: { only_available: true, per_page: 1 } });
                        if (nextRes.data.items.length) {
                            this.currentAccount = nextRes.data.items[0];
                            this.$message.info('已自动为您领取下一个可用账号');
                        } else {
                            this.currentAccount = null;
                            this.noAvailable = true;
                        }
                    }
                }
            } catch(e) {
                this.$message.error(e.response?.data?.error || '扣减失败');
            }
        },
        async useAll(accountId) {
            try {
                const res = await axios.post(`/api/accounts/${accountId}/use-all`);
                this.$message.success(res.data.message);
                await this.loadStats();
                await this.loadAccounts();
                const nextRes = await axios.get('/api/accounts', { params: { only_available: true, per_page: 1 } });
                if (nextRes.data.items.length) {
                    this.currentAccount = nextRes.data.items[0];
                    this.$message.info('已自动领取下一个账号，请复制使用');
                } else {
                    this.currentAccount = null;
                    this.noAvailable = true;
                }
            } catch(e) {
                this.$message.error(e.response?.data?.error || '操作失败');
            }
        },
        copyAccount(email) {
            const text = `${email}\n${this.unifiedPassword}`;
            navigator.clipboard.writeText(text);
            this.$message.success(`已复制 ${email} 和密码到剪贴板`);
        },
        onImportSuccess(response) {
            this.$message.success(`✅ 导入成功，共 ${response.imported} 个账号`);
            this.loadGroups();
            this.loadStats();
            this.loadAccounts();
        },
        onImportError() {
            this.$message.error('导入失败，CSV需包含email列');
        },
        async exportAccounts() {
            window.open('/api/accounts/export', '_blank');
        },
        async resetAllAccounts() {
            this.$confirm('此操作将把所有账号的今日已用次数清零，确定吗？', '提示', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }).then(async () => {
                const res = await axios.post('/api/accounts/reset-all');
                this.$message.success(`已重置 ${res.data.reset_count} 个账号`);
                this.loadStats();
                this.loadAccounts();
                this.currentAccount = null;
                this.noAvailable = false;
            }).catch(() => {});
        },
        resetAndLoad() {
            this.page = 1;
            this.loadAccounts();
            this.currentAccount = null;
            this.noAvailable = false;
        }
    }
}).use(ElementPlus).mount('#app');