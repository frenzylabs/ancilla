//
//  index.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 09/27/19
//  Copyright 2019 Wess Cope
//

import React from 'react'

import {
  Menu,
  Header
} from 'semantic-ui-react'

import ConnectionList from './list'

export default class Connections extends React.Component {
  render() {
    return(
      <Menu vertical compact borderless fluid style={{border: 'none', boxShadow: 'none'}}>
        <Menu.Item>
          <Header disabled dividing style={{margin:0}}>
            Ancilla
          </Header>
        </Menu.Item>

        <ConnectionList/>
      </Menu>
    )
  }
}
