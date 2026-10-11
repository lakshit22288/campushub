def campushub_user(request):
    return {"campushub_user": request.session.get("campushub_user")}
