from django.shortcuts import render,get_object_or_404,redirect
from django.views.generic import ListView, DetailView, View
from .models import BillingAddress, Item,Order,OrderItem,Payment
from django.utils import timezone
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import CheckoutForm
from django.conf import settings
import stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


# Create your views here.

class HomeView(ListView):
    model = Item
    paginate_by= 10
    template_name = 'home.html'


class OrderSummaryView(LoginRequiredMixin,View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user = self.request.user, ordered = False)
            context = {
                'object':order,
            }
            return render(self.request, 'order_summary.html', context)

        except ObjectDoesNotExist:
            messages.error(self.request, "You do not have an active order")
            return redirect("/")
    
# class ItemDetailView(DetailView):
#     model = Item
#     template_name ='products.html'


class ItemDetailView(DetailView):
    model = Item
    template_name ='product-page.html'

# def home(request):
#     context = {
#         'items':Item.objects.all()
#     }
#     return render(request, 'base.html',context)

# def products(request):
#     context = {
#         'items':Item.objects.all()
#     }
#     return render(request, 'products.html',context)



@login_required
def add_to_cart(request,slug):
    item = get_object_or_404(Item,slug=slug)
    order_item,created = OrderItem.objects.get_or_create(item = item, user = request.user, ordered = False)
    # order_item,created = OrderItem.objects.get_or_create(item = item)
    order_qs = Order.objects.filter(user=request.user,ordered=False)
    if order_qs.exists():
        order = order_qs[0]
# check if order item is in order
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity+=1
            order_item.save()
            messages.info(request,'This item was updated in cart')
            return redirect('core:order_summary')
        else:
            messages.info(request,'This item was added to cart')
            order.items.add(order_item)
            return redirect('core:order_summary')
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(user = request.user, ordered_date = ordered_date)
        order.items.add(order_item)
        messages.info(request,'This item was added to cart')
    return redirect('core:order_summary')




# remove from cart
@login_required
def remove_single_item_from_cart(request, slug):
    item = get_object_or_404(Item,slug=slug)
    order_qs = Order.objects.filter(user=request.user,ordered=False)
    if order_qs.exists():
        order = order_qs[0]
# check if order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item =  OrderItem.objects.get_or_create(item = item, user = request.user, ordered = False)[0]
            if order_item.quantity > 1:
                order_item.quantity-=1
                order_item.save()
            else:
                order.items.remove(order_item)
            
            messages.info(request,'quatity was updated')
            return redirect('core:order_summary' )
            # order.items.remove(order_item)
        else:
            #message
            messages.info(request,'Item not in cart')
            return redirect('core:product',slug=slug)
    else:
        #message
        messages.info(request,'User does not have an active order')
        return redirect('core:product', slug = slug)
    return redirect('core:product', slug=slug)
   


# remove from cart
@login_required
def remove_from_cart(request, slug):
    item = get_object_or_404(Item,slug=slug)
    order_qs = Order.objects.filter(user=request.user,ordered=False)
    if order_qs.exists():
        order = order_qs[0]
# check if order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item =  OrderItem.objects.get_or_create(item = item, user = request.user, ordered = False)[0]
            messages.info(request,'This item was removed from cart')
            order.items.remove(order_item)
        else:
            #message
            messages.info(request,'You do not have an active order')
            return redirect('core:product',slug=slug)
    else:
        #message
        messages.info(request,'User does not have an active order')
        return redirect('core:product', slug = slug)
    return redirect('core:product', slug=slug)
   



#    Checkoutview

class CheckoutView(View):
    def get(self, *args, **kwargs):
        form = CheckoutForm()
        context = {'form':form}
        return render(self.request, 'checkout.html',context)


    def post(self, *args, **kwargs):   
        form = CheckoutForm(self.request.POST or None)
        try:
            order = Order.objects.get(user = self.request.user, ordered = False)
            if form.is_valid():
                street_address = form.cleaned_data.get('street_address')
                appartment_address = form.cleaned_data.get('appartment_address')
                country = form.cleaned_data.get('country')
                zip = form.cleaned_data.get('zip')
                #Add functionality for this section
                # save_billing = form.cleaned_data.get('save_billing')
                # save_info = form.cleaned_data.get('save_info')
                payment_option = form.cleaned_data.get('payment_option')
                billing_address = BillingAddress(
                    user = self.request.user,
                    street_address=street_address,
                    appartment_address = appartment_address,
                    country = country,
                    zip = zip

                )
                billing_address.save()
                order.billing_address = billing_address
                order.save()
                # add redirects to payment option: stripe
                return redirect( 'core:checkout')
            messages.warning(self.request, 'failed checkout')
            return redirect( 'core:checkout')

        except ObjectDoesNotExist:
            messages.error(self.request, "You do not have an active order")
            return redirect("core:order_summary")
        

        
    
class PaymentView(View):
    def get(self, *args, **kwargs):
        return render(self.request, 'payment.html')

    def post(self, *args, **kwargs):
        order = Order.objects.get(user = self.request.user, ordered = False)
        token = self.request.POST.get('stripeToken')
        amount=int(order.get_total() * 100)


        try:
            # Use Stripe's library to make requests...
            charge = stripe.Charge.create(
                amount=amount,
                currency="usd",
                source=token,
                description="My First Test Charge (created for API docs)",
                )
            payment = Payment()
            payment.stripe_charge_id = charge['id']
            payment.user = self.request.user
            payment.amount = order.get_total()
            payment.save()

            order.ordered = True
            order.payment = payment
            order.save()
            messages.success(self.request, 'Your order was succesful')
            return redirect("/")
        except stripe.error.CardError as e:
            # Since it's a decline, stripe.error.CardError will be caught
            body = e.json_body
            err = body.get('error', {})
            messages.error(self.request, f"{err.get('message')}")
            return redirect("/")
          
        except stripe.error.RateLimitError as e:
            # Too many requests made to the API too quickly
            messages.error(self.request, 'rate limit error')
            return redirect("/")
        except stripe.error.InvalidRequestError as e:
            # Invalid parameters were supplied to Stripe's API
            messages.error(self.request, 'Invalid parameter error')
            return redirect("/")
        except stripe.error.AuthenticationError as e:
            # Authentication with Stripe's API failed
            # (maybe you changed API keys recently)
            messages.error(self.request, 'Authentication Error')
            return redirect("/")
        except stripe.error.APIConnectionError as e:
            # Network communication with Stripe failed
            messages.error(self.request, 'Api connection error')
            return redirect("/")
        except stripe.error.StripeError as e:
            # Display a very generic error to the user, and maybe send
            # yourself an email
            messages.error(self.request, 'something went wrong, You were not charged, please try again')
            return redirect("/")
        except Exception as e:
            # Something else happened, completely unrelated to Stripe
            messages.error(self.request, 'serious error has occured')
            return redirect("/")




        
        # order.ordered = True
      
