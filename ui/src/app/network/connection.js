//
//  connection.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 10/03/19
//  Copyright 2019 Wess Cope
//

import React      from 'react'
import {connect}  from 'react-redux'

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

    this.connect      = this.connect.bind(this)
    this.send         = this.send.bind(this)
    this.onConnect    = this.onConnect.bind(this)
    this.onDisconnect = this.onDisconnect.bind(this)
    this.onError      = this.onError.bind(this)
    this.onMessage    = this.onMessage.bind(this)

  }

  connect() {
    console.log("Connecting")

    this.socket = new WebSocket(`ws://${this.host}:${this.port}/serial`)

    this.socket.onopen = (e) => {
      this.onConnect(e)
    }

    this.socket.onclose = (e) => {
      this.onDisconnect(e)
    }


    this.socket.onerror = (err) => {
      this.onerror(err)
    }
    
    this.socket.onmessage = (e) => {
      this.onMessage(e)
    }
  }

  disconnect() {
    this.socket.send(JSON.stringify({
      action: 'disconnect'
    }))

    this.socket.disconnect()
  }

  send(message) {
    this.socket.send(message)
  }

  onConnect(event) {
    let message = JSON.stringify({
      action:   'connect',
      port:     this.path,
      baudrate: this.baudrate
    })

    this.send(message)
  }

  onDisconnect(event) {
    console.log("Disconnect: ", event)
  }

  onError(error) {
    console.log("Error: ", error)
  }

  onMessage(event) {
    if(this.onMessageHandler) {
      this.onMessageHandler(event.data)
    }
  }
}
