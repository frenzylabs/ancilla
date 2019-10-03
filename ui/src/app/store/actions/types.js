//
//  types.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 10/01/19
//  Copyright 2019 Wess Cope
//


export default {
  printer: {
    create:     "PRINTER.CREATE",
    list:       "PRINTER.LIST",
    ports:      "PRINTER.PORTS",
    error:      "PRINTER.ERROR"
  },
  notification: {
    info:     "NOTIFICATION.INFO",
    success:  "NOTIFICATION.SUCCESS",
    warning:  "NOTIFICATION.WARNING",
    failure:  "NOTIFICATION.FAILURE",
    dismiss:  "NOTIFICATION.DISMISS"
  },
  connection: {
    connect:      "SOCKET.CONNECT",
    connected:    "SOCKET.CONNECTED",
    disconnected: "SOCKET.DISCONNECTED",
    received:     "SOCKET.RECEIVED"
  }
}
