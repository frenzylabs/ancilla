//
//  printer.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 09/30/19
//  Copyright 2019 Wess Cope
//

import Request from './request'
import {printer} from '../store/actions'

export default {
  create: (printer) => {
    return (dispatch) => {
      return Request.post('/printers', printer)
        .then(response => {
          dispatch(actions.connection.create())
        })
        .catch(error => {
          throw(error)
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
          throw(error)
        })
    }
  },

  // ports: () => {
  //   return Request.get('/ports')
  //     .then(response => {
  //       dispatch(actions.connection.ports(response.data))
  //     })
  //     .catch(error => {
  //       throw(error)
  //     })
  // }
}
