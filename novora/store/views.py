from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.db.models import Q
from .models import Product, Category, Cart, CartItem, Wishlist, Order, OrderItem, Review, UserProfile
from .forms import RegisterForm, ProfileForm, ReviewForm, CheckoutForm
from django.contrib.auth.models import User
import json
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


# ---------- HOME ----------
def home(request):
    featured = Product.objects.filter(is_featured=True, stock_quantity__gt=0)[:8]
    eastern_cats = Category.objects.filter(category_type='eastern')
    western_cats = Category.objects.filter(category_type='western')
    new_arrivals = Product.objects.filter(stock_quantity__gt=0).order_by('-created_at')[:6]
    return render(request, 'store/home.html', {
        'featured': featured,
        'eastern_cats': eastern_cats,
        'western_cats': western_cats,
        'new_arrivals': new_arrivals,
    })


# ---------- PRODUCTS ----------
def product_list(request):
    products = Product.objects.filter(stock_quantity__gt=0)
    categories = Category.objects.all()

    cat_slug = request.GET.get('category')
    cat_type = request.GET.get('type')
    search = request.GET.get('search', '')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    fabric = request.GET.get('fabric')

    if cat_slug:
        products = products.filter(category__slug=cat_slug)
    if cat_type:
        products = products.filter(category__category_type=cat_type)
    if search:
        products = products.filter(Q(name__icontains=search) | Q(description__icontains=search))
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)
    if fabric:
        products = products.filter(fabric__icontains=fabric)

    return render(request, 'store/product_list.html', {
        'products': products,
        'categories': categories,
        'search': search,
    })


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    reviews = product.reviews.all().order_by('-created_at')
    review_form = ReviewForm()

    user_has_ordered = False
    if request.user.is_authenticated:
        user_has_ordered = OrderItem.objects.filter(
            order__user=request.user, product=product, order__status='delivered'
        ).exists()

        if request.method == 'POST':
            review_form = ReviewForm(request.POST)
            already_reviewed = Review.objects.filter(user=request.user, product=product).exists()
            if review_form.is_valid() and user_has_ordered and not already_reviewed:
                r = review_form.save(commit=False)
                r.user = request.user
                r.product = product
                r.save()
                messages.success(request, 'Review submitted!')
                return redirect('product_detail', slug=slug)

    return render(request, 'store/product_detail.html', {
        'product': product,
        'reviews': reviews,
        'review_form': review_form,
        'user_has_ordered': user_has_ordered,
    })


# ---------- AUTH ----------
def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user)
            Cart.objects.create(user=user)
            Wishlist.objects.create(user=user)
            login(request, user)
            messages.success(request, f'Welcome to NOVORA, {user.first_name}!')
            return redirect('home')
    else:
        form = RegisterForm()
    return render(request, 'store/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect(request.GET.get('next', 'home'))
        else:
            messages.error(request, 'Invalid username or password. Please try again.')
    return render(request, 'store/login.html')


def logout_view(request):
    logout(request)
    return redirect('home')


# ---------- PROFILE ----------
@login_required
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated!')
            return redirect('profile')
    else:
        form = ProfileForm(instance=profile)
    orders = request.user.orders.all().order_by('-created_at')
    return render(request, 'store/profile.html', {'form': form, 'orders': orders})


# ---------- CART ----------
@login_required
def cart_view(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    return render(request, 'store/cart.html', {'cart': cart})


@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart, _ = Cart.objects.get_or_create(user=request.user)
    size = request.POST.get('size', 'M')
    item, created = CartItem.objects.get_or_create(cart=cart, product=product, size=size)
    if not created:
        item.quantity += 1
        item.save()
    messages.success(request, f'"{product.name}" added to cart!')
    return redirect(request.META.get('HTTP_REFERER', 'cart'))


@login_required
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    item.delete()
    return redirect('cart')


@login_required
def update_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    qty = int(request.POST.get('quantity', 1))
    if qty > 0:
        item.quantity = qty
        item.save()
    else:
        item.delete()
    return redirect('cart')


# ---------- WISHLIST ----------
@login_required
def wishlist_view(request):
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    return render(request, 'store/wishlist.html', {'wishlist': wishlist})


@login_required
def toggle_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    if product in wishlist.products.all():
        wishlist.products.remove(product)
        messages.info(request, 'Removed from wishlist.')
    else:
        wishlist.products.add(product)
        messages.success(request, 'Added to wishlist!')
    return redirect(request.META.get('HTTP_REFERER', 'wishlist'))


# ---------- CHECKOUT ----------
@login_required
def checkout_view(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    if not cart.items.exists():
        messages.warning(request, 'Your cart is empty.')
        return redirect('cart')

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user
            order.total_amount = cart.total_price()
            order.save()
            for item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    size=item.size,
                    price=item.product.price
                )
                item.product.stock_quantity -= item.quantity
                item.product.save()
            cart.items.all().delete()
            messages.success(request, f'Order #{order.id} placed successfully!')
            return redirect('order_success', order_id=order.id)
    else:
        profile = getattr(request.user, 'profile', None)
        initial = {}
        if profile:
            initial = {'full_name': request.user.get_full_name(), 'email': request.user.email, 'phone': profile.phone, 'address': profile.address}
        form = CheckoutForm(initial=initial)

    return render(request, 'store/checkout.html', {'form': form, 'cart': cart})


def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'store/order_success.html', {'order': order})


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'store/order_detail.html', {'order': order})


# ============================================================
# AI STYLIST & BODY TYPE RECOMMENDATION ENGINE
# ============================================================

def _calculate_body_type(gender, bust, waist, hips):
    """
    Scientifically analyzes proportions to determine body shape.
    Measurements are in inches (normalized).
    """
    if gender.lower() == 'male':
        # 1. Oval / Round (waist is widest)
        if waist >= bust and waist >= hips:
            return {
                'key': 'oval',
                'name': 'Oval / Round Build',
                'badge_icon': 'bi-circle',
                'tagline': 'Fuller midsection with softer shoulders and narrower limbs.',
                'goal': 'Elongate the torso, create structure at the shoulders, and draw attention upward.',
                'eastern': {
                    'best_cuts': ['Straight-cut Kurtas with vertical stitching', 'Dark solid-toned Shalwar Kameez', 'Lightweight Nehru / Waistcoat jackets left unbuttoned or tailored'],
                    'fabrics': ['Crisp Cotton', 'Linen', 'Matte Silk', 'Structured Blends'],
                    'necklines': ['Mandarin collar / Band collar', 'Clean V-placket'],
                    'styling_tip': 'Pair monochromatic dark or neutral tones from top to bottom for a slimming vertical line.'
                },
                'western': {
                    'best_cuts': ['Structured single-breasted blazers (2-button)', 'Straight-leg trousers with flat front', 'Vertical striped shirts', 'Layered open overshirts'],
                    'fabrics': ['Lightweight wool', 'Twill', 'Oxford cotton'],
                    'necklines': ['Pointed collar', 'V-neck knitwear'],
                    'styling_tip': 'Avoid horizontal stripes and tight waistbands; opt for structured shoulders.'
                },
                'dos': ['Wear vertical patterns and dark solid colors', 'Choose structured shoulders on jackets and blazers', 'Keep waistbands flat and comfortable'],
                'donts': ['Avoid clingy fabrics like thin jersey', 'Avoid large bold horizontal prints', 'Avoid skinny-fit tapered pants']
            }
        # 2. Triangle (hips or waist wider than chest)
        elif hips > 1.05 * bust or waist > 1.05 * bust:
            return {
                'key': 'triangle_men',
                'name': 'Triangle Build',
                'badge_icon': 'bi-triangle',
                'tagline': 'Narrower chest and shoulders with wider waist and hips.',
                'goal': 'Add volume and structure to your upper body and shoulders while streamlining the lower half.',
                'eastern': {
                    'best_cuts': ['Kurtas with chest embroidery or pocket detail', 'Structured waistcoats with shoulder padding', 'Straight-fit trousers in dark tones'],
                    'fabrics': ['Stiff Cotton', 'Khaddar', 'Linen Blends', 'Textured Wool'],
                    'necklines': ['Embroidered collar / Ban', 'Contrasting yoke'],
                    'styling_tip': 'Waistcoats with shoulder definition and chest pockets draw attention upward.'
                },
                'western': {
                    'best_cuts': ['Structured single-breasted blazers with shoulder pads', 'Button-downs with chest pockets', 'Straight-fit dark jeans', 'Layered jackets with wide collars'],
                    'fabrics': ['Structured cotton', 'Medium-weight denim', 'Corduroy'],
                    'necklines': ['Wide spread collar', 'Horizontal stripe tees on chest'],
                    'styling_tip': 'Light-colored tops with dark bottoms create an instant broadening effect for the shoulders.'
                },
                'dos': ['Choose tops with chest details and structured shoulders', 'Wear dark straight-cut pants', 'Use light colors on top and dark colors below'],
                'donts': ['Avoid polo shirts that cling tightly to the waist', 'Avoid skinny jeans and tapered trousers', 'Avoid horizontal stripes across waist']
            }
        # 3. Inverted Triangle / Athletic V-Taper
        elif bust >= 1.20 * waist and bust >= 1.08 * hips:
            return {
                'key': 'inverted_triangle_men',
                'name': 'Inverted Triangle (Athletic V-Taper)',
                'badge_icon': 'bi-triangle-fill',
                'tagline': 'Broad shoulders and chest tapering down to a narrow waist and hips.',
                'goal': 'Balance your broad upper body with straight or relaxed bottoms without hiding your athletic build.',
                'eastern': {
                    'best_cuts': ['Fitted Kurta with straight silhouette', 'Tailored Prince coats & Waistcoats', 'Classic Shalwar or Straight Troumar Pajama'],
                    'fabrics': ['Raw Silk', 'Textured Cotton', 'Linen', 'Jacquard'],
                    'necklines': ['Band Collar (Ban)', 'Classic Sherwani collar'],
                    'styling_tip': 'Showcase your shoulders with fitted waistcoats; avoid overly padded shoulders.'
                },
                'western': {
                    'best_cuts': ['Slim-fit / Athletic-fit crew necks and polos', 'Straight or relaxed-fit jeans & chinos', 'Unstructured blazers', 'Horizontal striped casual tees'],
                    'fabrics': ['Breathable cotton', 'Chambray', 'Stretch denim'],
                    'necklines': ['Crew neck', 'Wide collar shirts', 'Polo collar'],
                    'styling_tip': 'Straight-leg trousers balance out wide shoulders effortlessly.'
                },
                'dos': ['Wear athletic cut tops that highlight the taper', 'Choose straight-leg trousers to balance broad shoulders', 'Opt for subtle clean necklines'],
                'donts': ['Avoid excessive shoulder padding in jackets', 'Avoid ultra-skinny jeans that exaggerate upper width', 'Avoid wide boat necks']
            }
        # 4. Trapezoid (Balanced athletic)
        elif bust >= 1.08 * waist:
            return {
                'key': 'trapezoid',
                'name': 'Trapezoid (Classic Athletic Proportions)',
                'badge_icon': 'bi-gem',
                'tagline': 'Naturally balanced proportions with broad shoulders, well-fitted chest, and tapered waist.',
                'goal': 'Highlight your versatile, naturally balanced proportions with modern tailored cuts.',
                'eastern': {
                    'best_cuts': ['Tailored Kurta Pajama', 'Embroidered Sherwanis', 'Double-breasted Waistcoats', 'Straight-cut cotton Kurtas'],
                    'fabrics': ['Lawn', 'Wash & Wear', 'Silk', 'Linen', 'Karandi'],
                    'necklines': ['Mandarin Collar', 'Sherwani Collar', 'Buttoned Placket'],
                    'styling_tip': 'Almost all Eastern cuts flatter your frame. Experiment with rich textures and festive waistcoats.'
                },
                'western': {
                    'best_cuts': ['Slim-fit button-downs', 'Tailored suits & sports coats', 'Slim-straight denim', 'Layered bomber & leather jackets'],
                    'fabrics': ['Fine cotton', 'Denim', 'Merino wool', 'Textured linen'],
                    'necklines': ['Notched lapels', 'Crew & V-necks', 'Classic spread collar'],
                    'styling_tip': 'Take advantage of fitted silhouettes that trace your natural contours.'
                },
                'dos': ['Wear tailored and structured fits', 'Experiment with bold patterns, colors, and layering', 'Keep waistbands clean and fitted'],
                'donts': ['Avoid overly baggy or boxy garments that hide your natural shape', 'Avoid disproportionate extremes']
            }
        # 5. Rectangle
        else:
            return {
                'key': 'rectangle_men',
                'name': 'Rectangle Build',
                'badge_icon': 'bi-square',
                'tagline': 'Shoulders, chest, and waist are of similar width creating a straight silhouette.',
                'goal': 'Create the illusion of broader shoulders and a tapered waist through layering and smart cuts.',
                'eastern': {
                    'best_cuts': ['Layered Kurta with structured Waistcoat', 'Kurtas with angled shoulder embroidery', 'Sherwanis with structured chest plates'],
                    'fabrics': ['Textured Cotton', 'Jacquard', 'Linen', 'Silk Blends'],
                    'necklines': ['Mandarin collar', 'Double placket detail'],
                    'styling_tip': 'A contrast waistcoat over a solid kurta instantly adds depth and shoulder definition.'
                },
                'western': {
                    'best_cuts': ['Structured blazers with padded shoulders', 'Layered jackets over crew neck tees', 'Slim-fit chinos with belt', 'Tops with chest pockets'],
                    'fabrics': ['Textured knits', 'Heavy cotton', 'Tweed', 'Denim'],
                    'necklines': ['Wide lapels', 'Crew neck', 'Horizontal pattern tops'],
                    'styling_tip': 'Layering jackets and wearing belts adds horizontal definition where needed.'
                },
                'dos': ['Layer with jackets and waistcoats', 'Wear structured blazers with defined shoulders', 'Use textured fabrics to add dimension'],
                'donts': ['Avoid shapeless baggy t-shirts', 'Avoid overly tight vertical monochromatic looks without layering']
            }
    else:
        # Female classifications
        b_h_diff = abs(bust - hips) / max(bust, hips, 1)
        w_b_ratio = waist / max(bust, 1)
        w_h_ratio = waist / max(hips, 1)

        # 1. Apple / Round (waist is widest or almost equal to bust/hips)
        if (waist >= 0.95 * bust and waist >= 0.95 * hips) or (waist > bust or waist > hips):
            return {
                'key': 'apple',
                'name': 'Apple / Round Shape',
                'badge_icon': 'bi-circle',
                'tagline': 'Fuller bust and midsection with slender arms, shapely legs, and hips.',
                'goal': 'Elongate the torso, draw attention to your neckline and legs, and skim effortlessly over the midsection.',
                'eastern': {
                    'best_cuts': ['Empire waist Kurtas', 'Straight-cut long Kurtis with high side slits', 'A-line Tunics in flowing fabrics', 'Front-open long shrugs and capes over monochrome inner sets'],
                    'fabrics': ['Soft Georgette', 'Chiffon', 'Cotton-Silk', 'Flowing Lawn'],
                    'necklines': ['V-neck', 'Deep scoop', 'Vertical button-down placket', 'Angrakha style'],
                    'styling_tip': 'Long flowing vertical shrugs or drapes create vertical slimming panels instantly.'
                },
                'western': {
                    'best_cuts': ['Empire waist dresses', 'Flowy tunic tops with straight-leg jeans', 'A-line shift dresses', 'Longline open cardigans and unbuttoned blazers', 'Wrap tops tied loosely'],
                    'fabrics': ['Lightweight cotton', 'Rayon', 'Crepe', 'Soft linen'],
                    'necklines': ['V-neck', 'Sweetheart', 'Keyhole'],
                    'styling_tip': 'Showcase your fabulous legs with knee-length tunics, dresses, and straight-leg trousers.'
                },
                'dos': ['Wear flowing fabrics that drape without clinging to midriff', 'Opt for empire waistlines and vertical lines', 'Highlight your neckline and slender legs'],
                'donts': ['Avoid tight belts cinched directly across the stomach', 'Avoid heavy horizontal ruffles or pocket details across waist', 'Avoid stiff, boxy fabrics']
            }
        # 2. Hourglass (balanced bust and hips, narrow waist)
        elif b_h_diff <= 0.08 and w_b_ratio <= 0.77 and w_h_ratio <= 0.77:
            return {
                'key': 'hourglass',
                'name': 'Hourglass Figure',
                'badge_icon': 'bi-hourglass-split',
                'tagline': 'Balanced bust and hips with a beautifully defined, narrow waistline.',
                'goal': 'Highlight your natural curves and celebrate your waist definition without adding bulk.',
                'eastern': {
                    'best_cuts': ['Fit-and-flare Anarkalis with fitted bodice', 'Belted Kurtas and Kaftans', 'Angrakha style dresses', 'Straight-cut Kurti with high-waist palazzo or churidar', 'Flattering Peplum tops'],
                    'fabrics': ['Georgette', 'Chiffon', 'Silk', 'Flowing Lawn', 'Crepe'],
                    'necklines': ['Sweetheart', 'V-Neck', 'Angrakha Wrap', 'Scoop Neck'],
                    'styling_tip': 'Drape your dupatta diagonally across the shoulder or cinch it with a statement belt at the waist.'
                },
                'western': {
                    'best_cuts': ['Wrap dresses and wrap tops', 'Bodycon & mermaid dresses', 'High-waisted tailored trousers & pencil skirts', 'Fitted blazers with single-button closure', 'Fit-and-flare midi dresses'],
                    'fabrics': ['Stretch crepe', 'Soft knit', 'Satin', 'Viscose'],
                    'necklines': ['V-neck', 'Wrap neckline', 'Sweetheart', 'Square neck'],
                    'styling_tip': 'Belts and high-waist bottoms are your best friends to accentuate your natural waist.'
                },
                'dos': ['Emphasize your waist with belts, fitted cuts, and wrap styles', 'Choose fluid, body-contouring fabrics', 'Opt for open necklines that balance your bust'],
                'donts': ['Avoid shapeless oversized boxy tunics that hide your waist', 'Avoid stiff, heavy fabrics that add unwanted bulk', 'Avoid high bulky turtlenecks without waist cinching']
            }
        # 3. Pear / Triangle (hips significantly larger than bust)
        elif hips > 1.05 * bust:
            return {
                'key': 'pear',
                'name': 'Pear / Triangle Shape',
                'badge_icon': 'bi-triangle',
                'tagline': 'Hips and thighs are wider than shoulders/bust, with an elegant defined waist.',
                'goal': 'Draw attention upward to your neckline and shoulders while draping smoothly over the hips.',
                'eastern': {
                    'best_cuts': ['A-Line Kurtas and flared Anarkalis', 'Embroidered neckline Kurtis', 'Front-open jackets with straight pants', 'Flowing Ghararas with short Kurtis', 'Kaftans with embellished yokes'],
                    'fabrics': ['Chiffon', 'Silk', 'Lawn', 'Georgette', 'Jacquard'],
                    'necklines': ['Boat neck', 'Wide V-neck', 'Heavily embroidered collars', 'Square neck'],
                    'styling_tip': 'Opt for bright/printed Kurtis paired with dark, straight-cut trousers to balance proportions.'
                },
                'western': {
                    'best_cuts': ['A-line skirts and skater dresses', 'Tops with ruffled or puffed sleeves', 'Wide-leg high-rise trousers', 'Tailored blazers hitting above or below hip widest point', 'Off-shoulder tops'],
                    'fabrics': ['Cotton poplin', 'Chambray', 'Flowy rayon', 'Structured blends'],
                    'necklines': ['Off-shoulder', 'Boat neck', 'Bateau', 'Cowl neck'],
                    'styling_tip': 'Draw the eye upward with statement sleeves, statement collars, and detailed necklaces.'
                },
                'dos': ['Choose A-line cuts and flared skirts that skim over hips', 'Wear detailed, vibrant tops and embellished necklines', 'Opt for boat necks and puff sleeves to broaden shoulders'],
                'donts': ['Avoid tight low-rise jeans or clingy bodycon skirts', 'Avoid pocket details or heavy embroidery directly on the hip line', 'Avoid boxy tunics that end at the widest part of your hips']
            }
        # 4. Inverted Triangle (bust significantly wider than hips)
        elif bust > 1.05 * hips:
            return {
                'key': 'inverted_triangle',
                'name': 'Inverted Triangle Shape',
                'badge_icon': 'bi-triangle-fill',
                'tagline': 'Bust and shoulders are broader than hips, with athletic slender legs.',
                'goal': 'Add volume, movement, and flair to your lower half while softening the shoulder line.',
                'eastern': {
                    'best_cuts': ['Flared Shararas & Ghararas with simple tops', 'Tiered Anarkalis with simple yokes', 'A-line Kurtis with flared hem and side slits', 'Palazzo sets with minimal shoulder detail'],
                    'fabrics': ['Silk', 'Organza', 'Georgette', 'Chiffon', 'Linen'],
                    'necklines': ['Deep V-Neck', 'Scoop neck', 'U-neck', 'Vertical plackets'],
                    'styling_tip': 'Focus embroidery, prints, and embellishments on the hemline, shalwar, or dupatta rather than the shoulders.'
                },
                'western': {
                    'best_cuts': ['Pleated skirts & flared A-line dresses', 'Wide-leg palazzo pants and boyfriend jeans', 'Peplum tops that flare at hips', 'Wrap dresses with flared skirts', 'Deep V-neck blouses'],
                    'fabrics': ['Soft draping knits', 'Satin', 'Fluid silk', 'Denim'],
                    'necklines': ['Deep V-neck', 'Halter neck', 'Asymmetrical neck'],
                    'styling_tip': 'Pair simple, dark tops with printed or wide-leg flared bottoms to create instant visual symmetry.'
                },
                'dos': ['Wear wide-leg trousers, palazzos, and flared skirts', 'Choose deep V-necks and vertical necklines', 'Add bold prints, bright colors, and volume on bottom'],
                'donts': ['Avoid exaggerated shoulder pads or puff sleeves', 'Avoid wide boat necks that broaden shoulders further', 'Avoid skinny jeans with oversized bulky tops']
            }
        # 5. Rectangle (Athletic / Straight)
        else:
            return {
                'key': 'rectangle',
                'name': 'Rectangle / Athletic Shape',
                'badge_icon': 'bi-square',
                'tagline': 'Bust, waist, and hips are fairly aligned, creating a sleek, athletic, straight silhouette.',
                'goal': 'Create dimension, feminine curves, and waist definition through textured layers and flared cuts.',
                'eastern': {
                    'best_cuts': ['Angrakha Kurtas that tie at waist', 'Peplum tops with flared Gharara / Sharara', 'Tiered Anarkalis with embroidered yoke', 'Belted Kaftans and flared tunics', 'Short Kurtis with voluminous Shalwars'],
                    'fabrics': ['Organza', 'Jacquard', 'Raw Silk', 'Textured Lawn', 'Embroidered Net'],
                    'necklines': ['Sweetheart', 'Boat neck', 'Round with keyhole', 'Embellished collar'],
                    'styling_tip': 'Use belts, tiered layers, and flared silhouettes to add shape and depth to your look.'
                },
                'western': {
                    'best_cuts': ['Fit-and-flare dresses', 'High-waisted paperbag trousers and belted shorts', 'Ruffled & peplum blouses', 'Cut-out dresses and wrap tops', 'Cropped jackets layered over dresses'],
                    'fabrics': ['Textured knits', 'Poplin', 'Taffeta', 'Denim', 'Lace'],
                    'necklines': ['Off-shoulder', 'Sweetheart', 'Halter neck', 'Cowl neck'],
                    'styling_tip': 'Belted outerwear and ruffled peplum tops create instant curve illusions.'
                },
                'dos': ['Add dimension with ruffles, belts, pleats, and peplums', 'Wear fit-and-flare silhouettes and belted dresses', 'Experiment with bold prints and rich textures'],
                'donts': ['Avoid straight shapeless shift dresses without waist styling', 'Avoid severe square boxy cuts that accentuate straight lines']
            }


# ---------- AI STYLIST API ----------
@csrf_exempt
def ai_stylist_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            gender = data.get('gender', 'female').strip().lower()
            unit = data.get('unit', 'in').strip().lower()
            style_pref = data.get('style_pref', 'all').strip().lower()
            occasion = data.get('occasion', 'all').strip().lower()

            try:
                bust = float(data.get('bust', 0))
                waist = float(data.get('waist', 0))
                hips = float(data.get('hips', 0))
                height = float(data.get('height', 0)) if data.get('height') else 0
            except (ValueError, TypeError):
                return JsonResponse({'error': 'Please provide valid numerical measurements.'}, status=400)

            if bust <= 0 or waist <= 0 or hips <= 0:
                return JsonResponse({'error': 'Please enter positive measurements for bust/chest, waist, and hips.'}, status=400)

            # Convert cm to inches for standard calculation if needed
            bust_in = bust / 2.54 if unit == 'cm' else bust
            waist_in = waist / 2.54 if unit == 'cm' else waist
            hips_in = hips / 2.54 if unit == 'cm' else hips
            height_in = height / 2.54 if (unit == 'cm' and height > 0) else height

            # Calculate Body Shape
            body_type_data = _calculate_body_type(gender, bust_in, waist_in, hips_in)

            # Calculate Ratios
            bw_ratio = round(waist_in / max(bust_in, 1), 2)
            hw_ratio = round(waist_in / max(hips_in, 1), 2)

            # Query Store Products matching the user's style preferences & silhouette
            products_qs = Product.objects.filter(stock_quantity__gt=0)
            if style_pref == 'eastern':
                products_qs = products_qs.filter(category__category_type='eastern')
            elif style_pref == 'western':
                products_qs = products_qs.filter(category__category_type='western')

            # Fetch top products
            recommended_products = []
            selected_products = list(products_qs[:6])
            for p in selected_products:
                recommended_products.append({
                    'id': p.id,
                    'name': p.name,
                    'slug': p.slug,
                    'price': str(p.price),
                    'category_name': p.category.name if p.category else 'Fashion',
                    'category_type': p.category.category_type if p.category else 'all',
                    'image_url': p.image.url if p.image else '',
                    'fabric': p.fabric or 'Premium'
                })

            # AI Stylist Note generation via OpenRouter or fallback expert message
            ai_note = f"Based on your {bust} x {waist} x {hips} {unit} measurements, your silhouette is classified as a **{body_type_data['name']}**. For {occasion if occasion != 'all' else 'any event'}, focusing on {body_type_data['goal'].lower()} will create your most confident, breathtaking look in Novora's premium collection."

            # Attempt OpenRouter call if API Key is configured
            import os
            from django.conf import settings
            api_key = "YOUR_OPENROUTER_API_KEY"
            env_path = os.path.join(settings.BASE_DIR, '.env')
            try:
                with open(env_path, 'r') as f:
                    for line in f:
                        if line.strip().startswith('chatbot_API_Key'):
                            api_key = line.split('=', 1)[1].strip().strip('"').strip("'")
                            break
            except Exception:
                api_key = os.environ.get('chatbot_API_Key', api_key)

            if api_key and api_key != "YOUR_OPENROUTER_API_KEY":
                try:
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "http://localhost:8000/",
                        "X-Title": "Novora AI Stylist"
                    }
                    prompt = f"""
You are the Lead Haute Couture Fashion Stylist for Novora, a luxury Pakistani fashion house offering Eastern & Western wear.
A customer has entered their body measurements:
- Gender: {gender}
- Bust/Chest: {bust} {unit}
- Waist: {waist} {unit}
- Hips: {hips} {unit}
- Calculated Body Shape: {body_type_data['name']}
- Preferred Style: {style_pref}
- Occasion: {occasion}

Give a warm, high-end, inspiring, 2-3 sentence personalized styling note on how to style Novora outfits for this body shape to look exquisite. Keep it uplifting and fashionable.
"""
                    payload = {
                        "model": "openrouter/auto",
                        "messages": [
                            {"role": "system", "content": "You are a professional luxury fashion stylist. Keep your advice chic, positive, and concise (2-3 sentences max)."},
                            {"role": "user", "content": prompt}
                        ]
                    }
                    ai_res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=2.5)
                    ai_data = ai_res.json()
                    if 'choices' in ai_data and len(ai_data['choices']) > 0:
                        ai_note = ai_data['choices'][0]['message']['content'].strip()
                except Exception:
                    pass # Fallback to default expert note

            response_payload = {
                'success': True,
                'body_type': body_type_data,
                'user_inputs': {
                    'gender': gender,
                    'unit': unit,
                    'bust': bust,
                    'waist': waist,
                    'hips': hips,
                    'height': height,
                    'style_pref': style_pref,
                    'occasion': occasion
                },
                'proportions': {
                    'waist_to_bust': bw_ratio,
                    'waist_to_hip': hw_ratio
                },
                'ai_note': ai_note,
                'recommended_products': recommended_products
            }
            return JsonResponse(response_payload)

        except Exception as e:
            return JsonResponse({'error': f"Failed to calculate style: {str(e)}"}, status=500)

    return JsonResponse({'error': 'POST request required'}, status=400)


# ---------- CHATBOT ----------
@csrf_exempt
def chatbot_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '')

            # OpenRouter API Integration
            import os
            from django.conf import settings
            
            api_key = "YOUR_OPENROUTER_API_KEY"
            env_path = os.path.join(settings.BASE_DIR, '.env')
            try:
                with open(env_path, 'r') as f:
                    for line in f:
                        if line.strip().startswith('chatbot_API_Key'):
                            api_key = line.split('=', 1)[1].strip().strip('"').strip("'")
                            break
            except Exception:
                api_key = os.environ.get('chatbot_API_Key', api_key)
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:8000/",
                "X-Title": "Novora Chatbot"
            }
            
            system_prompt = """
You are the professional AI Stylist & Support Bot for Novora, a premium Eastern and Western fashion e-commerce brand based in Bahawalpur, Pakistan. 
Be highly professional, chic, polite, and helpful. 
Important details:
- Contact: support@novora.pk, +92 301 8380666.
- We sell both Eastern Wear and Western Wear.
- You can give instant fashion advice based on body shapes (Hourglass, Pear, Inverted Triangle, Rectangle, Apple for women; Trapezoid, Inverted Triangle, Rectangle, Triangle, Oval for men).
- Answer FAQ's concisely: standard shipping takes 3-5 days; we accept Cash on Delivery (COD); returns are accepted within 7 days for unworn items.
Keep answers brief, stylish, and helpful (1-3 sentences max).
"""
            
            payload = {
                "model": "openrouter/auto",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
            }

            if api_key == "YOUR_OPENROUTER_API_KEY":
                return JsonResponse({"reply": "Hello! I am your Novora Fashion Assistant. Try clicking the 'AI Stylist' button in the navbar for a full body measurement analysis, or ask me about our Eastern and Western collections, shipping, and sizes!"})

            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload
            )
            
            response_data = response.json()
            if 'choices' in response_data and len(response_data['choices']) > 0:
                bot_reply = response_data['choices'][0]['message']['content']
            else:
                error_msg = response_data.get('error', {}).get('message', str(response_data))
                bot_reply = f"Error from AI Provider: {error_msg}"
                
            return JsonResponse({"reply": bot_reply})
            
        except Exception as e:
            return JsonResponse({"reply": f"An error occurred: {str(e)}"})
    return JsonResponse({"error": "Invalid request method"}, status=400)