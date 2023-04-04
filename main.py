from website import create_app,socketHandler

app = create_app()

if __name__ == '__main__':
    socketHandler.socketio.run(app=app,debug=True, host="0.0.0.0", port = 5000)



    