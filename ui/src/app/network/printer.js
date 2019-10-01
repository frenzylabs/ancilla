//
//  printer.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 09/30/19
//  Copyright 2019 Wess Cope
//

import Request    from './request'
import {printer}  from '../store/actions'

const _printer = {
  create: (printer) => {
    return (dispatch) => {
      return Request.post('/printers', printer)
        .then(response => {
          dispatch(_printer.list())
        })
        .catch(error => {
          dispatch(printer.error(error))
        })
    }
  },

  list: () => {
    return (dispatch) => {
      return Request.get('/printers')
        .then(response => {
          dispatch(printer.list(response.data))
        })
        .catch(error => {
          dispatch(printer.error(error))
        })
    }
  },

  ports: () => {
    return (dispatch) => {
      return Request.get('/ports')
        .then(response => {
          dispatch(printer.ports(response.data))
        })
        .catch((error) => {
          dispatch(printer.error(error))
        })
    }
  }
}

export default _printer
