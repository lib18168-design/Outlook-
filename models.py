from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date

db = SQLAlchemy()


class OutlookAccount(db.Model):
    __tablename__ = 'outlook_accounts'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    # 密码统一，不需要存每个账号的密码（或者存一次全局密码）
    daily_used = db.Column(db.Integer, default=0)  # 今日已使用次数 0-5
    last_used_date = db.Column(db.Date, default=date.today)  # 最后使用日期
    notes = db.Column(db.Text)
    group_name = db.Column(db.String(50), default='default')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def remaining_today(self):
        """今日剩余次数"""
        if self.last_used_date != date.today():
            return 5  # 新的一天，重置为5
        return 5 - self.daily_used

    def use_one(self):
        """使用一次，扣减剩余次数"""
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
            'remaining': self.remaining_today,
            'last_used_date': self.last_used_date.strftime('%Y-%m-%d'),
            'notes': self.notes,
            'group_name': self.group_name
        }