//
//  index.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 09/27/19
//  Copyright 2019 Wess Cope
//

import React from 'react'

import ConnectionList from './list'

export default class Connections extends React.Component {
  render() {
    return (
      <React.Fragment>
        <ConnectionList/>
      </React.Fragment>
    )
  }
}
