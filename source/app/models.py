import datetime
from hashlib import md5

from flask import url_for
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from . import db, lm, whooshee
from .utils import markdown_to_html


class Admin(UserMixin, db.Model):
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    site_name = db.Column(db.String(4))
    site_title = db.Column(db.String(255))
    name = db.Column(db.String(4))
    profile = db.Column(db.String(255))
    login_name = db.Column(db.String(500))
    password_hash = db.Column(db.String(500))

    record_info = db.Column(db.String(255), nullable=True)

    def __init__(self, **kwargs):
        super(Admin, self).__init__(**kwargs)

    # 对密码进行加密保存
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<Admin %r>' % (self.name)

@lm.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))

class LoveMe(db.Model):
    __tablename__ = 'loveme'
    id = db.Column(db.Integer, primary_key=True)
    loveMe = db.Column(db.Integer, default=666)

    def __init__(self, loveMe):
        self.loveMe = loveMe

    def __repr__(self):
        return '<LoveMe %r>' % (self.loveMe)

class Page(db.Model):
    __tablename__ = 'pages'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(6))
    url_name = db.Column(db.String(25))
    canComment = db.Column(db.Boolean, default=False)
    isNav = db.Column(db.Boolean, default=False)
    body = db.Column(db.Text)

    comments = db.relationship('Comment', backref='page', lazy='dynamic')

    @property
    def body_to_html(self):
        html = markdown_to_html(self.body)
        return html

    def to_json(self):
        page = {
            'id': self.id,
            'title': self.title,
            'url': self.url_name,
            'api': url_for('api.get_page', id=self.id, _external=True),
            'isNav': self.isNav,
            'comment_count': self.comments.count() if self.canComment else None,
            'comments': url_for('api.get_page_comments', id=self.id, _external=True) if self.canComment else None
        }
        return page

    def __repr__(self):
        return '<Page %r>' % (self.title)

@whooshee.register_model('title', 'body')
class Post(db.Model):
    """为了把文章缓存时间久一些，把文章浏览量模型分离"""
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64))
    url_name = db.Column(db.String(64))
    timestamp = db.Column(db.String(64))
    # view_num = db.Column(db.Integer, default=0)
    body = db.Column(db.Text)
    draft = db.Column(db.Boolean, default=False)
    disable = db.Column(db.Boolean, default=False)

    tags = db.Column(db.String(64))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    comments = db.relationship('Comment', backref='post', lazy='dynamic')

    @property
    def timestampInt(self):
        return int(''.join([i for i in self.timestamp.split('-')]))
    @property
    def year(self):
        return int([i for i in self.timestamp.split('-')][0])
    @property
    def month(self):
        return int([i for i in self.timestamp.split('-')][1])

    def tag_in_post(self, tag):
        if self.tags.find(',') > -1:
            tags = [i for i in self.tags.split(',')]
            if tag in tags:
                return True
            return False
        else:
            if tag == self.tags:
                return True
            return False

    @property
    def body_to_html(self):
        html = markdown_to_html(self.body)
        return html

    def to_json(self):
        post = {
            'id': self.id,
            'title': self.title,
            'api': url_for('api.get_post', id=self.id, _external=True),
            'datetime': self.timestamp,
            'category': self.category.category,
            'tag': self.tags,
            'comment_count': self.comments.count(),
            'comments': url_for('api.get_post_comments', id=self.id, _external=True)
        }
        return post

    def to_dict(self):
        """缓存"""
        post = {
            'id': self.id,
            'url': self.url_name,
            'title': self.title,
            'body': self.body_to_html,
            'year': self.year,
            'month': self.month,
            'datetime': self.timestamp,
            'category': self.category.category,
            'tag': self.tags,
            'comment_count': self.comments.filter_by(disabled=True).count()
        }
        return post

    def __repr__(self):
        return '<Post %r>' % (self.title)

class View(db.Model):
    """文章浏览量"""
    __tablename__ = 'views'
    id = db.Column(db.Integer, primary_key=True)
    count = db.Column(db.Integer, default=0)
    type = db.Column(db.String(25), default='post')

    relationship_id = db.Column(db.Integer)

class Comment(db.Model):
    """
    缓存设计尝试：
        取消原先的模型关联，
        增加type键｛
            'post': 博客文章评论
            'page': 博客页面评论
            'article': 专栏文章评论
        ｝
        以type和id来获取对于评论
    """
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    comment = db.Column(db.Text)
    author = db.Column(db.String(25))
    email = db.Column(db.String(255))
    website = db.Column(db.String(255), nullable=True)
    isReply = db.Column(db.Boolean, default=False)
    replyTo = db.Column(db.Integer, nullable=True)
    disabled = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.datetime.now)

    # type = db.Column(db.String(25), default='post')
    # relationship_id = db.Column(db.Integer)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))
    page_id = db.Column(db.Integer, db.ForeignKey('pages.id'))
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'))

    def __init__(self, **kwargs):
        super(Comment, self).__init__(**kwargs)

        if self.website:
            if self.website.startswith('http://') or self.website.startswith('https://'):
                self.website = self.website
            else:
                self.website = 'http://' + self.website

    @property
    def strptime(self):
        return datetime.datetime.strftime(self.timestamp, '%Y-%m-%d')

    @property
    def body_to_html(self):
        html = markdown_to_html(self.comment)
        return html

    # 获取Gravatar头像
    def gravatar(self, size):
        return 'http://www.gravatar.com/avatar/' + md5(self.email.encode('utf-8')).hexdigest() + '?d=mm&s=' + str(size)

    def to_json(self):
        comment = {
            'id': self.id,
            'isReply': self.isReply,
            'author': self.author,
            'avatar': self.gravatar(38),
            'mail': self.email,
            'site': self.website,
            'datetime': self.strptime,
            'comment': self.body_to_html
        }
        if self.isReply:
            comment['avatar'] = self.gravatar(26)
            comment['replyTo'] = self.replyTo
        return comment

    def __repr__(self):
        return '<Comment %r>' %(self.comment)

class Tag(db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True)
    tag = db.Column(db.String(25), index=True)

    def to_json(self):
        tag = {
            'tag': self.tag,
            'posts': url_for('api.get_tag_posts', tag=self.tag, _external=True)
        }
        return tag

    def __repr__(self):
        return '<Tag %r>' % (self.tag)

class Category(db.Model):
    __tablename__ = 'category'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(6), index=True)

    posts = db.relationship('Post', backref='category', lazy='dynamic')

    def to_json(self):
        category = {
            'category': self.category,
            'post_count': self.posts.count(),
            'posts': url_for('api.get_category_posts', category=self.category, _external=True)
        }
        return category

    def __repr__(self):
        return '<Category %r>' % (self.category)

class SiteLink(db.Model):
    __tablename__ = 'sitelinks'
    id = db.Column(db.Integer, primary_key=True)
    link = db.Column(db.String(125))
    name = db.Column(db.String(25))
    isFriendLink = db.Column(db.Boolean)
    isGreatLink = db.Column(db.Boolean, default=True)
    info = db.Column(db.String(125), nullable=True)

    def __repr__(self):
        return '<SiteLink %r>' % (self.link)

class Shuoshuo(db.Model):
    __tablename__ = 'shuos'
    id = db.Column(db.Integer, primary_key=True)
    shuo = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.datetime.now)

    def __init__(self, shuo):
        self.shuo = shuo

    @property
    def strptime(self):
        return datetime.datetime.strftime(self.timestamp, '%Y-%m-%d')
    @property
    def year(self):
        return int([i for i in self.strptime.split('-')][0])
    @property
    def month_and_day(self):
        return [i for i in self.strptime.split('-')][1] + '/' + [i for i in self.strptime.split('-')][2]

    @property
    def body_to_html(self):
        html = markdown_to_html(self.shuo)
        return html

    def to_json(self):
        shuo = {
            'shuo': self.shuo,
            'datetime': self.strptime
        }
        return shuo

    def __repr__(self):
        return '<Shuoshuo %r>' % (self.shuo)


class Column(db.Model):
    __tablename__ = 'columns'
    id = db.Column(db.Integer, primary_key=True)
    column = db.Column(db.String(64))
    url_name = db.Column(db.String(64))
    body = db.Column(db.Text)
    view_num = db.Column(db.Integer, default=0)
    love_num = db.Column(db.Integer, default=0)
    timestamp = db.Column(db.String(64))
    password_hash = db.Column(db.String(500))

    articles = db.relationship('Article', backref='column', lazy='dynamic')

    @property
    def body_to_html(self):
        html = markdown_to_html(self.body)
        return html

    # 对密码进行加密保存
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password) if password else None

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<Column %r>' % (self.column)

class Article(db.Model):
    __tablename__ = 'articles'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64))
    # view_num = db.Column(db.Integer, default=0)
    body = db.Column(db.Text)
    secrecy = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.String(64))

    column_id = db.Column(db.Integer, db.ForeignKey('columns.id'))
    comments = db.relationship('Comment', backref='article', lazy='dynamic')

    @property
    def body_to_html(self):
        html = markdown_to_html(self.body)
        return html

    def to_dict(self):
        article = {
            'id': self.id,
            'title': self.title,
            'body': self.body_to_html,
            'secrecy': self.secrecy,
            'timestamp': self.timestamp,
            'column': self.column.column,
            'comment_count': self.comments.count()
        }
        return article

    def __repr__(self):
        return '<Article %r>' % (self.title)


class SideBox(db.Model):
    __tablename__ = 'side_boxes'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64), nullable=True)
    body = db.Column(db.Text)
    unable = db.Column(db.Boolean, default=False)
    is_advertising = db.Column(db.Boolean)

    def __repr__(self):
        return '<SideBox %r>' % (self.body)


class Alembic(db.Model):
    __tablename__ = 'alembic_version'
    version_num = db.Column(db.String(32), primary_key=True, nullable=False)

    @staticmethod
    def clear_A():
        for a in Alembic.query.all():
            db.session.delete(a)
        db.session.commit()
