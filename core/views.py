from django.shortcuts import redirect


def home(request):
    if request.user.is_authenticated:
        return redirect('chat_ui')
    return redirect('login')
