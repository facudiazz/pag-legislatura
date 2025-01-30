from flask import (
    Flask,
    request,
    render_template,
    send_file,
    redirect,
    url_for,
    flash,
    jsonify,
    session,
    Response,
)
from sqlalchemy import create_engine, or_, func, and_
from sqlalchemy.orm import sessionmaker
from io import BytesIO
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import desc
from database_setup import File, User, Attachment, AdminUser, Events, CustomField

app = Flask(__name__, static_url_path="/static")
app.secret_key = "supersecretkey"
app.config["SESSION_PERMANENT"] = False
engine = create_engine("sqlite:///files.db")
Session = sessionmaker(bind=engine)
db_session = Session()

CATEGORY_NAMES = {
    "Categoria1": "Leyes",
    "Categoria2": "Resoluciones",
    "Categoria3": "Declaraciones",
    "Categoria4": "Hace Consideraciones",
    "Categoria5": "Escuelas",
    "Categoria6": "Remite Actuaciones",
    "Categoria7": "Sancionados",
    "Categoria8": "Caducidades",
    "Categoria9": "Segundo y Tercer Giro",
    "Categoria10": "Asesores Doc.",
}


def regular_user_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session and session["user_id"] is not None:
            return f(*args, **kwargs)
        else:
            flash("Esta acción solo está permitida para usuarios registrados.")
            return redirect(url_for("index"))

    return decorated_function


def custom_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" not in session or not session["logged_in"]:
            flash("Para poder ver este contenido es necesario iniciar sesión")
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


def admin_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "admin_logged_in" not in session or not session["admin_logged_in"]:
            flash("Acceso no autorizado. Por favor, inicia sesión como administrador.")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)

    return decorated_function


@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        admin_user = db_session.query(AdminUser).filter_by(username=username).first()
        if admin_user and admin_user.check_password(password):
            session["admin_logged_in"] = True
            flash("Iniciaste sesión como administrador correctamente.")
            return redirect(url_for("admin_panel"))
        else:
            flash("Credenciales incorrectas. Por favor, intenta de nuevo.")

    return render_template("admin_login.html")


@app.route("/add_admin", methods=["GET", "POST"])
def add_admin():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if not db_session.query(AdminUser).filter_by(username=username).first():
            admin_user = AdminUser(username=username)
            admin_user.set_password(password)
            db_session.add(admin_user)
            db_session.commit()
            flash("Usuario administrador creado correctamente", "success")
        else:
            flash(
                "Ya existe un usuario administrador con ese nombre de usuario", "error"
            )

        return redirect(url_for("admin_login"))

    return render_template("add_admin.html")


@app.route("/")
@custom_login_required
def index():
    categories = (
        db_session.query(File.category, func.count(File.id))
        .group_by(File.category)
        .all()
    )
    return render_template(
        "index.html", categories=categories, CATEGORY_NAMES=CATEGORY_NAMES
    )

from werkzeug.exceptions import BadRequest

@app.route("/upload", methods=["POST"])
@regular_user_required
def upload_file():
    try:
        file = request.files["file"]
        category = request.form["category"]
        expediente = request.form["expediente"]
        autor_coautor = request.form["autor_coautor"]
        sumario = request.form["sumario"]
        fecha_ingreso = datetime.strptime(request.form["fecha_ingreso"], "%Y-%m-%d").strftime("%d/%m/%Y")
        giros_posteriores = request.form["giros_posteriores"]
        antecedentes = request.form["antecedentes"]
        relaciones = request.form["relaciones"]

        new_filename = f"{expediente}.pdf"

        new_file = File(
            name=new_filename,
            data=file.read(),
            category=category,
            expediente=expediente,
            autor_coautor=autor_coautor,
            sumario=sumario,
            fecha_ingreso=fecha_ingreso,
            giros_posteriores=giros_posteriores,
            antecedentes=antecedentes,
            relaciones=relaciones,
            downloaded_by=None,
        )

        db_session.add(new_file)
        db_session.flush()

        custom_field_count = 0
        while True:
            custom_name_key = f"custom_field_name_{custom_field_count}"
            if custom_name_key not in request.form:
                break

            name = request.form[custom_name_key]

            # Since we are only handling text fields now, type is hardcoded as 'text'
            field_type = 'text'

            custom_value_key = f"custom_field_value_{custom_field_count}"
            value = request.form.get(custom_value_key, '')

            custom_field = CustomField(
                file_id=new_file.id,
                name=name,
                type=field_type,
                value=value
            )
            db_session.add(custom_field)
            custom_field_count += 1

        attachments = request.files.getlist("attachments")
        if attachments:
            for index, attachment in enumerate(attachments):
                if attachment.filename:
                    ext = attachment.filename.split(".")[-1]
                    if len(attachments) == 1:
                        new_attachment_name = f"Anexo.{ext}"
                    else:
                        new_attachment_name = f"Anexo{index + 1}.{ext}"

                    new_attachment = Attachment(
                        name=new_attachment_name,
                        data=attachment.read(),
                        file_id=new_file.id
                    )
                    db_session.add(new_attachment)

        db_session.commit()

        flash("Expediente cargado correctamente")
        return redirect(url_for("index"))

    except BadRequest as e:
        flash(f"Error en la solicitud: {str(e)}", category="error")
        return redirect(url_for("index"))

@app.route("/download/<int:file_id>")
def download_file(file_id):
    file = db_session.query(File).get(file_id)
    if file:
        return Response(
            file.data,
            mimetype="application/pdf",
            headers={"Content-Disposition": "inline; filename=" + file.name},
        )
    else:
        flash("Archivo no encontrado")
        return redirect(url_for("search_file", query=request.args.get("query")))


@app.route("/delete/<int:file_id>", methods=["POST"])
@regular_user_required
def delete_file(file_id):
    file = db_session.query(File).get(file_id)
    if file:
        db_session.delete(file)
        db_session.commit()
        flash("Expediente eliminado correctamente", "success")
    else:
        flash("El expediente no existe", "error")
    return redirect(request.referrer)

from sqlalchemy import or_, and_

from sqlalchemy import or_, and_

@app.route("/search", methods=["GET"])
@custom_login_required
def search_file():
    query = request.args.get("query")
    category = request.args.get("category")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    expediente = request.args.get("expediente")
    sumario = request.args.get("sumario")
    autor_coautor = request.args.get("autor_coautor")

    query_filters = []

    if query:
        query_filters.append(or_(
            File.name.like(f"%{query}%"),
            File.category.like(f"%{query}%"),
        ))

    if category and category != "Categoria7":
        query_filters.append(File.category == category)

    if start_date:
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            query_filters.append(File.fecha_ingreso >= start_date)
        except ValueError:
            flash("Formato de fecha de inicio no válido. Utilice el formato aaaa-mm-dd")
            return redirect(url_for("index"))

    if end_date:
        try:
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            query_filters.append(File.fecha_ingreso <= end_date)
        except ValueError:
            flash(
                "Formato de fecha de finalización no válido. Utilice el formato aaaa-mm-dd"
            )
            return redirect(url_for("index"))

    if expediente:
        query_filters.append(File.expediente.like(f"%{expediente}%"))

    if sumario:
        query_filters.append(File.sumario.like(f"%{sumario}%"))

    if autor_coautor:
        query_filters.append(or_(
            File.autor_coautor.like(f"%{autor_coautor}%"),
            File.autor_coautor.like(f"%{autor_coautor}%")
        ))

    if category == "Categoria7":
        query_filters.append(File.category == "Categoria7")
    else:
        query_filters.append(File.category != "Categoria7")

    query = db_session.query(File)

    if query_filters:
        query = query.filter(and_(*query_filters))

    files = query.all()

    return render_template(
        "search_result.html", files=files, CATEGORY_NAMES=CATEGORY_NAMES
    )

@app.route("/edit/<int:file_id>", methods=["GET", "POST"])
@custom_login_required
def edit_file(file_id):
    file = db_session.query(File).get(file_id)
    attachments = db_session.query(Attachment).filter_by(file_id=file_id).all()

    if request.method == "POST":
        if request.form["action"] == "Save":
            file.name = request.form["name"]
            file.category = request.form["category"]
            file.expediente = request.form["expediente"]
            file.autor_coautor = request.form["autor_coautor"]
            file.sumario = request.form["sumario"]
            file.fecha_ingreso = datetime.strptime(
                request.form["fecha_ingreso"], "%d/%m/%Y"
            ).strftime("%d/%m/%Y")
            file.giros_posteriores = request.form["giros_posteriores"]
            file.antecedentes = request.form["antecedentes"]
            file.relaciones = request.form["relaciones"]

            delete_attachments = request.form.getlist("delete_attachment")
            for attachment_id in delete_attachments:
                attachment = db_session.query(Attachment).get(attachment_id)
                if attachment:
                    db_session.delete(attachment)

            new_attachments = request.files.getlist("attachments")
            for attachment in new_attachments:
                if attachment.filename:
                    ext = attachment.filename.split(".")[-1]
                    new_attachment_name = generate_unique_attachment_name(file_id, ext)
                    new_attachment = Attachment(
                        name=new_attachment_name, data=attachment.read(), file_id=file_id
                    )
                    db_session.add(new_attachment)

            db_session.commit()

            flash("Expediente editado correctamente", "success")
            return redirect(url_for("index"))

    return render_template("edit_file.html", file=file, attachments=attachments)

def generate_unique_attachment_name(file_id, ext):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"Anexo_{file_id}_{timestamp}.{ext}"

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        if "username" in request.form and "password" in request.form:
            username = request.form["username"]
            password = request.form["password"]
            user = db_session.query(User).filter_by(username=username).first()
            if user and user.check_password(password):
                session["logged_in"] = True
                session["user_id"] = user.id
                flash("Iniciaste sesión correctamente")

                return redirect(url_for("index"))
            else:
                flash("Usuario o contraseña incorrecto/s")
                return redirect(url_for("login"))
        elif "guest_password" in request.form:
            guest_password = request.form["guest_password"]
            if guest_password == "invitado@decom":
                session["logged_in"] = True
                session["user_id"] = None
                flash("Iniciaste sesión como invitado")
                return redirect(url_for("index"))
            else:
                flash("Contraseña de invitado incorrecta")
                return redirect(url_for("login"))
        else:
            flash("Por favor, ingresa tus credenciales o la contraseña de invitado")
            return redirect(url_for("login"))
    return render_template("login.html")


@app.route("/admin", methods=["GET", "POST"])
@admin_login_required
def admin_panel():
    if request.method == "POST":
        if "username" in request.form and "password" in request.form:
            username = request.form["username"]
            password = request.form["password"]
            if db_session.query(User).filter_by(username=username).first():
                flash("Ya existe un usuario con ese nombre", "error")
            else:
                new_user = User(username=username)
                new_user.set_password(password)
                db_session.add(new_user)
                db_session.commit()
                flash("Usuario registrado correctamente", "success")

        elif "username_to_delete" in request.form:
            username_to_delete = request.form["username_to_delete"]
            user_to_delete = (
                db_session.query(User).filter_by(username=username_to_delete).first()
            )
            if user_to_delete:
                db_session.delete(user_to_delete)
                db_session.commit()
                flash("Usuario eliminado correctamente", "success")
            else:
                flash("El usuario no existe", "error")

    return render_template("admin_panel.html")


@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    session.pop("user_id", None)
    session.pop("admin_logged_in", None)
    return redirect(url_for("login"))


@app.route("/download_attachment/<int:attachment_id>")
def download_attachment(attachment_id):
    attachment = db_session.query(Attachment).get(attachment_id)
    if attachment:
        return Response(
            attachment.data,
            mimetype="application/pdf",
            headers={"Content-Disposition": "inline; filename=" + attachment.name},
        )
    else:
        flash("Archivo anexo no encontrado")
        return redirect(url_for("index"))


@app.route("/update_file_names", methods=["GET"])
@admin_login_required
def update_file_names_route():
    files = db_session.query(File).all()

    for file in files:
        expediente = file.expediente
        new_filename = f"{expediente}.pdf"
        if file.name != new_filename:
            file.name = new_filename
            db_session.commit()

    flash("File names updated successfully.")
    return redirect(url_for("admin_panel"))


@app.route("/preview/<int:file_id>")
@custom_login_required
def preview_file(file_id):
    file = db_session.query(File).get(file_id)
    if file:
        if file.name.endswith(".pdf"):
            pdf_url = url_for("download_file", file_id=file_id)
            user_agent = request.user_agent.string
            if 'iPad' in user_agent or 'iPhone' in user_agent:
                return render_template("preview_pdf_ios.html", file=file, pdf_url=pdf_url)
            else:
                return render_template("preview_pdf.html", file=file, pdf_url=pdf_url)
        else:
            flash("No hay preview disponible para ese tipo de archivos.")
    else:
        flash("Archivo no encontrado")

    return redirect(url_for("search_file", query=request.args.get("query")))


@app.route("/delete_attachment/<int:attachment_id>", methods=["POST"])
@regular_user_required
def delete_attachment(attachment_id):
    attachment = db_session.query(Attachment).get(attachment_id)
    if attachment:
        db_session.delete(attachment)
        db_session.commit()
        flash("Archivo anexo eliminado correctamente", "success")
    else:
        flash("El archivo anexo no existe", "error")
    return redirect(request.referrer)


@app.route("/calendar", methods=["GET", "POST"])
@regular_user_required
def calendar():
    return render_template("calendar.html")


@app.route("/load_events")
@regular_user_required
def load_events():
    try:
        with Session() as session:
            events = session.query(Events).all()
            formatted_events = []
            for event in events:
                formatted_events.append(
                    {
                        "id": event.id,
                        "title": event.title,
                        "start": event.start.isoformat(),
                        "end": event.end.isoformat(),
                    }
                )
        return jsonify(formatted_events)

    except Exception as e:
        print(f"Error al cargar eventos: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/add_event", methods=["POST"])
@regular_user_required
def add_event():
    try:
        title = request.form["title"]

        start = datetime.fromisoformat(request.form["start"].replace("T", " "))
        end = datetime.fromisoformat(request.form["end"].replace("T", " "))

        with Session() as session:
            new_event = Events(title=title, start=start, end=end)
            session.add(new_event)
            session.commit()

        return jsonify({"message": "Evento agregado correctamente"})

    except Exception as e:
        print(f"Error al guardar el evento: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/delete_event/<int:event_id>", methods=["DELETE"])
@regular_user_required
def delete_event(event_id):
    try:
        with Session() as session:
            event = session.query(Events).get(event_id)
            if event:
                session.delete(event)
                session.commit()

                return redirect(url_for('calendar'))
            else:
                return jsonify({"error": "Evento no encontrado"}), 404
    except Exception as e:
        print(f"Error al eliminar el evento: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/load_events_by_date/<date_str>")
@regular_user_required
def load_events_by_date(date_str):
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
        with Session() as session:
            events = session.query(Events).filter(func.date(Events.start) == date).all()
            formatted_events = [
                {"title": e.title, "start": e.start, "end": e.end} for e in events
            ]
        return jsonify(formatted_events)
    except Exception as e:
        print(f"Error al cargar eventos por fecha: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/search_expedientes", methods=["GET", "POST"])
def search_expedientes():
    return render_template("search_expedientes.html")


if __name__ == "__main__":
    app.run(debug=True)
