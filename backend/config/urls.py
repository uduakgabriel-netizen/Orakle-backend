from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse

def test_view(request):
    return HttpResponse("Orakle Backend is running!")

urlpatterns = [
    path('', test_view),  # Root URL test
    path('admin/', admin.site.urls),
    path('api/', include('wallets.urls')),
    path('api/', include('contracts.urls')),
    path('api/', include('transactions.urls')),
    path('api/', include('ai.urls')),
    path('api/', include('reports.urls')),
    path('api/', include('core.urls')),
    path('api/', include('solana.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
