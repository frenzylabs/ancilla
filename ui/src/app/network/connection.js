//
//  connection.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 10/03/19
//  Copyright 2019 Wess Cope
//

import React      from 'react'
import {connect}  from 'react-redux'
import io         from 'socket.io-client'

import {default as actions} from '../store/actions/connection'

export default class Connection {
  buffer  = []
  sent    = []

  constructor(props) {

    this.name     = props.name
    this.host     = 'localhost'
    this.port     = 5000
    this.path     = props.path
    this.baudrate = props.baudrate

    this.manager = io(`http://${this.host}:${this.port}`, {
      autoConnect: false,
      transports: ['websocket']
    })

    this.onConnect    = this.onConnect.bind(this)
    this.onDisconnect = this.onDisconnect.bind(this)
    this.onMessage    = this.onMessage.bind(this)
    this.send         = this.send.bind(this)

    this.manager.on('connect',  this.onConnect)
    this.manager.on('disconnect',  this.onDisconnect)
    this.manager.on('message',     this.onMessage)
  }

  connect() {
    console.log("Starting connection")

    this.manager.open()

    return this
  }

  disconnect() {
    this.socket.close()
  }

  onConnect(socket) {
    console.log("Connected")
    
    this.connected  = true
    this.socket     = socket

    store.dispatch(actions.connected(this))

    this.manager.emit('message', 'im here!!', (res) => {
      console.log("RES: ", res)
    })
  }

  onDisconnect() {
    console.log("Disconnected")

    this.connected = false
    
    store.dispatch(actions.disconnected(this))
  }

  onMessage(msg) {
    this.buffer.push(msg)
  }

  send(msg) {
    this.sent.push(msg)
    io.emit('message', msg)
  }
}
