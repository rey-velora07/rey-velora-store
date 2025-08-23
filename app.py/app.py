import os, json
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

app = Flask(__name__)
app.secret_key = "change_this_secret"

DATA_DIR = "data"
PRODUCTS_FILE = os.path.join(DATA_DIR, "products.json")
ORDERS_FILE   = os.path.join(DATA_DIR, "orders.json")

# ===== Helpers =====
def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(PRODUCTS_FILE):
        sample = [
            {
                "id": 1,
                "name": "فستان فيكتوري مطرّز",
                "price": 35.00,
                "description": "تفاصيل دانتيل مع قصّة كلاسيكية.",
                "image_url": "https://picsum.photos/400/520?1",
                "stock": 10,
                "active": True,
                "colors": ["أسود","أبيض","كحلي"],
                "sizes": ["XS","S","M","L","XL","XXL"]
            },
            {
                "id": 2,
                "name": "كورسيه كلاسيكي",
                "price": 22.50,
                "description": "كورسيه خامة متينة وخياطة أنيقة.",
                "image_url": "https://picsum.photos/400/520?2",
                "stock": 8,
                "active": True,
                "colors": ["بيج","أسود","عنابي"],
                "sizes": ["S","M","L","XL"]
            }
        ]
        with open(PRODUCTS_FILE,"w",encoding="utf-8") as f: json.dump(sample,f,ensure_ascii=False,indent=2)
    if not os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE,"w",encoding="utf-8") as f: json.dump([],f,ensure_ascii=False,indent=2)

def load_products():
    ensure_data_dir()
    with open(PRODUCTS_FILE,"r",encoding="utf-8") as f: return json.load(f)

def save_products(products):
    with open(PRODUCTS_FILE,"w",encoding="utf-8") as f: json.dump(products,f,ensure_ascii=False,indent=2)

def load_orders():
    ensure_data_dir()
    with open(ORDERS_FILE,"r",encoding="utf-8") as f: return json.load(f)

def save_orders(orders):
    with open(ORDERS_FILE,"w",encoding="utf-8") as f: json.dump(orders,f,ensure_ascii=False,indent=2)

def next_product_id(products):
    return (max([p["id"] for p in products]) + 1) if products else 1

ADMIN_EMAIL = "laalhashmy01@gmail.com"
ADMIN_PASSWORD = "reem.store.2007"

# ===== Public pages =====
@app.route("/")
def products_page():
    products = [p for p in load_products() if p.get("active", True)]
    return render_template("products.html", products=products, title="الرئيسية")

@app.route("/product/<int:pid>")
def product_detail(pid):
    products = load_products()
    product = next((p for p in products if p["id"]==pid), None)
    if not product or not product.get("active", True):
        flash("المنتج غير موجود", "danger")
        return redirect(url_for("products_page"))
    return render_template("product_detail.html", product=product, title=product["name"])

@app.route("/add_to_cart/<int:pid>", methods=["POST"])
def add_to_cart(pid):
    products = load_products()
    product = next((p for p in products if p["id"]==pid), None)
    if not product:
        flash("المنتج غير موجود", "danger")
        return redirect(url_for("products_page"))

    size  = request.form.get("size","")
    color = request.form.get("color","")
    use_custom = request.form.get("use_custom_size")
    custom = None
    if use_custom:
        custom = {
            "bust": request.form.get("bust") or "",
            "waist": request.form.get("waist") or "",
            "hips": request.form.get("hips") or "",
            "height": request.form.get("height") or "",
            "notes": request.form.get("size_notes") or ""
        }
    try:
        quantity = int(request.form.get("quantity","1"))
        if quantity < 1: raise ValueError
    except ValueError:
        flash("الكمية غير صحيحة", "danger")
        return redirect(url_for("product_detail", pid=pid))

    cart = session.get("cart", [])
    cart.append({
        "id": product["id"],
        "name": product["name"],
        "price": float(product["price"]),
        "quantity": quantity,
        "size": size if not use_custom else "",
        "color": color,
        "custom_size": custom
    })
    session["cart"] = cart
    flash("تمت إضافة المنتج للسلة", "success")
    return redirect(url_for("product_detail", pid=pid))

@app.route("/cart")
def cart():
    cart_items = session.get("cart", [])
    total = sum(item["price"]*item["quantity"] for item in cart_items)
    return render_template("cart.html", cart_items=cart_items, total=total, title="السلة")

@app.route("/update_cart/<int:index>", methods=["POST"])
def update_cart(index):
    cart = session.get("cart", [])
    if 0 <= index < len(cart):
        try:
            qty = int(request.form.get("quantity","1"))
            if qty < 1: raise ValueError
            cart[index]["quantity"] = qty
            session["cart"] = cart
            flash("تم تحديث الكمية", "success")
        except ValueError:
            flash("الكمية غير صحيحة", "danger")
    return redirect(url_for("cart"))

@app.route("/remove_from_cart/<int:index>")
def remove_from_cart(index):
    cart = session.get("cart", [])
    if 0 <= index < len(cart):
        cart.pop(index)
        session["cart"] = cart
        flash("تم الحذف من السلة", "success")
    return redirect(url_for("cart"))

@app.route("/checkout", methods=["GET","POST"])
def checkout():
    cart_items = session.get("cart", [])
    if not cart_items:
        flash("سلتك فارغة", "danger")
        return redirect(url_for("products_page"))

    total = sum(item["price"]*item["quantity"] for item in cart_items)
    if request.method == "POST":
        name    = request.form.get("name","").strip()
        email   = request.form.get("email","").strip()
        phone   = request.form.get("phone","").strip()
        address = request.form.get("address","").strip()
        note    = request.form.get("note","").strip()
        try:
            eta_days = int(request.form.get("eta_days","20"))
            if eta_days < 1: eta_days = 20
        except:
            eta_days = 20

        orders = load_orders()
        order_id = (orders[-1]["id"]+1) if orders else 1
        orders.append({
            "id": order_id,
            "name": name,
            "email": email,
            "phone": phone,
            "address": address,
            "note": note,
            "eta_days": eta_days,
            "items": cart_items,
            "total": total,
            "status": "معلق",
            "tracking_number": ""
        })
        save_orders(orders)
        session["cart"] = []
        return render_template("order_confirm.html", order_id=order_id, title="تم الطلب")
    return render_template("checkout.html", cart_items=cart_items, total=total, title="الدفع")

# ===== Admin auth =====
@app.route("/admin/login", methods=["GET","POST"])
def admin_login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        password = (request.form.get("password") or "").strip()
        if email.lower() == ADMIN_EMAIL.lower() and password == ADMIN_PASSWORD:
            session["user_email"] = email
            flash("تم تسجيل الدخول", "success")
            return redirect(url_for("admin_panel"))
        flash("البريد أو كلمة السر غير صحيحة", "danger")
    return render_template("admin_login.html", admin_email=ADMIN_EMAIL, title="دخول المصمّمة")

@app.route("/admin/logout")
def admin_logout():
    session.pop("user_email", None)
    flash("تم تسجيل الخروج", "success")
    return redirect(url_for("products_page"))

def admin_required():
    return session.get("user_email")

# ===== Admin panel =====
@app.route("/admin")
def admin_panel():
    if not admin_required(): return redirect(url_for("admin_login"))
    return render_template("admin_panel.html",
                           admin_email=session.get("user_email"),
                           products=load_products(),
                           orders=load_orders(),
                           title="لوحة التحكم")

# CRUD Products
@app.route("/admin/products/create", methods=["POST"])
def admin_products_create():
    if not admin_required(): return redirect(url_for("admin_login"))
    products = load_products()
    pid = next_product_id(products)
    p = {
        "id": pid,
        "name": request.form.get("name","").strip(),
        "price": float(request.form.get("price","0") or 0),
        "stock": int(request.form.get("stock","0") or 0),
        "image_url": request.form.get("image_url","").strip(),
        "description": request.form.get("description","").strip(),
        "colors": [c.strip() for c in (request.form.get("colors","")).split(",") if c.strip()],
        "sizes":  [s.strip() for s in (request.form.get("sizes","")).split(",")  if s.strip()],
        "active": True if request.form.get("active")=="on" else False
    }
    products.append(p)
    save_products(products)
    flash("تمت إضافة المنتج", "success")
    return redirect(url_for("admin_panel"))

@app.route("/admin/products/<int:pid>/update", methods=["POST"])
def admin_products_update(pid):
    if not admin_required(): return redirect(url_for("admin_login"))
    products = load_products()
    p = next((x for x in products if x["id"]==pid), None)
    if not p: 
        flash("المنتج غير موجود", "danger")
        return redirect(url_for("admin_panel"))
    p["name"]  = request.form.get("name","").strip()
    p["price"] = float(request.form.get("price","0") or 0)
    p["stock"] = int(request.form.get("stock","0") or 0)
    p["image_url"] = request.form.get("image_url","").strip()
    p["description"] = request.form.get("description","").strip()
    p["colors"] = [c.strip() for c in (request.form.get("colors","")).split(",") if c.strip()]
    p["sizes"]  = [s.strip() for s in (request.form.get("sizes","")).split(",")  if s.strip()]
    p["active"] = True if request.form.get("active")=="on" else False
    save_products(products)
    flash("تم حفظ التعديلات", "success")
    return redirect(url_for("admin_panel"))

@app.route("/admin/products/<int:pid>/delete")
def admin_products_delete(pid):
    if not admin_required(): return redirect(url_for("admin_login"))
    products = load_products()
    products = [x for x in products if x["id"]!=pid]
    save_products(products)
    flash("تم حذف المنتج", "success")
    return redirect(url_for("admin_panel"))

# Orders update
@app.route("/admin/orders/<int:oid>/update", methods=["POST"])
def admin_orders_update(oid):
    if not admin_required(): return redirect(url_for("admin_login"))
    orders = load_orders()
    o = next((x for x in orders if x["id"]==oid), None)
    if not o:
        flash("الطلب غير موجود", "danger")
        return redirect(url_for("admin_panel"))
    o["status"] = request.form.get("status", o.get("status",""))
    o["tracking_number"] = request.form.get("tracking_number", o.get("tracking_number",""))
    try:
        o["eta_days"] = int(request.form.get("eta_days", o.get("eta_days",20)))
    except:
        pass
    save_orders(orders)
    flash("تم تحديث الطلب", "success")
    return redirect(url_for("admin_panel"))

if __name__ == "__main__":
    ensure_data_dir()
    app.run(debug=True)