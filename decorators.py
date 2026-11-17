from functools import wraps
from flask import session, redirect, url_for, flash, abort

def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return view(**kwargs)
    return wrapped_view

def role_required(*allowed_roles):
    def decorator(view):
        @wraps(view)
        def wrapped_view(**kwargs):
            if 'user_id' not in session:
                flash('Please log in to continue.', 'warning')
                return redirect(url_for('auth.login'))

            user_role = session.get('role')
            if user_role not in allowed_roles:
                flash('You do not have permission to access that resource.', 'danger')
                abort(403)

            if user_role == 'examiner' and not session.get('is_approved', 0):
                flash('Your examiner registration is pending administrator approval.', 'warning')
                return redirect(url_for('auth.login'))

            return view(**kwargs)
        return wrapped_view
    return decorator
