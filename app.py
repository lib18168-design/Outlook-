from flask import Flask, request, jsonify, render_template, Response
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import date
import pandas as pd
import io

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///accounts.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
CORS(app)
db = SQLAlchemy(app)

UNIFIED_PASSWORD = "QQ159357a"


class OutlookAccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    daily_used = db.Column(db.Integer, default=0)
    last_used_date = db.Column(db.Date, default=date.today)
    notes = db.Column(db.Text, default='')
    group_name = db.Column(db.String(50), default='default')

    @property
    def remaining(self):
        if self.last_used_date != date.today():
            return 5
        return max(0, 5 - self.daily_used)

    def use_one(self):
        today = date.today()
        if self.last_used_date != today:
            self.daily_used = 1
            self.last_used_date = today
        else:
            self.daily_used += 1
        db.session.commit()

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'daily_used': self.daily_used,
            'remaining': self.remaining,
            'last_used_date': self.last_used_date.strftime('%Y-%m-%d'),
            'notes': self.notes,
            'group_name': self.group_name
        }


with app.app_context():
    db.create_all()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    only_available = request.args.get('only_available') == 'true'
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    search = request.args.get('search', '')
    group = request.args.get('group', '')

    query = OutlookAccount.query
    if only_available:
        today = date.today()
        query = query.filter(
            (OutlookAccount.last_used_date != today) | (OutlookAccount.daily_used < 5)
        )
    if search:
        query = query.filter(OutlookAccount.email.contains(search))
    if group and group != 'all':
        query = query.filter_by(group_name=group)

    pagination = query.paginate(page=page, per_page=per_page)
    return jsonify({
        'items': [a.to_dict() for a in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages,
        'unified_password': UNIFIED_PASSWORD
    })


@app.route('/api/accounts/<int:aid>/use', methods=['POST'])
def use_account(aid):
    acc = OutlookAccount.query.get_or_404(aid)
    if acc.remaining <= 0:
        return jsonify({'error': '今日次数已用完'}), 400
    acc.use_one()
    next_id = None
    if acc.remaining == 0:
        today = date.today()
        next_acc = OutlookAccount.query.filter(
            (OutlookAccount.last_used_date != today) | (OutlookAccount.daily_used < 5)
        ).first()
        if next_acc:
            next_id = next_acc.id
    return jsonify({
        'success': True,
        'remaining': acc.remaining,
        'message': f'已使用一次，剩余{acc.remaining}次',
        'next_id': next_id
    })


@app.route('/api/accounts/<int:aid>/use-all', methods=['POST'])
def use_all_account(aid):
    acc = OutlookAccount.query.get_or_404(aid)
    today = date.today()
    acc.daily_used = 5
    acc.last_used_date = today
    db.session.commit()
    return jsonify({
        'success': True,
        'message': f'账号 {acc.email} 今日5次已标记用完'
    })


@app.route('/api/accounts/batch', methods=['POST'])
def batch_import():
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    file = request.files['file']
    df = pd.read_csv(file)
    count = 0
    for _, row in df.iterrows():
        email = row.get('email')
        if not email:
            continue
        if not OutlookAccount.query.filter_by(email=email).first():
            acc = OutlookAccount(
                email=email,
                notes=row.get('notes', ''),
                group_name=row.get('group', 'default')
            )
            db.session.add(acc)
            count += 1
    db.session.commit()
    return jsonify({'imported': count})


@app.route('/api/accounts/<int:aid>', methods=['DELETE'])
def delete_account(aid):
    acc = OutlookAccount.query.get_or_404(aid)
    db.session.delete(acc)
    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/accounts/batch-delete', methods=['POST'])
def batch_delete():
    ids = request.json.get('ids', [])
    if not ids:
        return jsonify({'error': 'No ids'}), 400
    OutlookAccount.query.filter(OutlookAccount.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({'deleted': len(ids)})


@app.route('/api/accounts/reset-all', methods=['POST'])
def reset_all():
    today = date.today()
    accounts = OutlookAccount.query.all()
    for acc in accounts:
        acc.daily_used = 0
        acc.last_used_date = today
    db.session.commit()
    return jsonify({'reset_count': len(accounts)})


@app.route('/api/accounts/export', methods=['GET'])
def export_accounts():
    accounts = OutlookAccount.query.all()
    data = [{
        'email': a.email,
        'daily_used': a.daily_used,
        'remaining': a.remaining,
        'last_used_date': a.last_used_date.strftime('%Y-%m-%d'),
        'notes': a.notes,
        'group': a.group_name
    } for a in accounts]
    df = pd.DataFrame(data)
    output = io.BytesIO()
    df.to_csv(output, index=False, encoding='utf-8-sig')
    output.seek(0)
    return Response(output, mimetype='text/csv',
                    headers={"Content-Disposition": "attachment;filename=accounts_export.csv"})


@app.route('/api/groups', methods=['GET'])
def get_groups():
    groups = db.session.query(OutlookAccount.group_name).distinct().all()
    return jsonify([g[0] for g in groups if g[0]])


@app.route('/api/stats', methods=['GET'])
def stats():
    total = OutlookAccount.query.count()
    today = date.today()
    available = OutlookAccount.query.filter(
        (OutlookAccount.last_used_date != today) | (OutlookAccount.daily_used < 5)
    ).count()
    used_today = sum([a.daily_used for a in OutlookAccount.query.filter_by(last_used_date=today).all()])
    total_capacity = total * 5
    return jsonify({
        'total': total,
        'available': available,
        'used_today': used_today,
        'total_capacity': total_capacity,
        'remaining_today': total_capacity - used_today,
        'unified_password': UNIFIED_PASSWORD
    })


if __name__ == '__main__':
    app.run(debug=True, port=5000)