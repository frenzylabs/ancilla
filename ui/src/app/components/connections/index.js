//
//  index.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 09/27/19
//  Copyright 2019 Wess Cope
//

import React      from 'react'
import {connect}  from 'react-redux'

import {
  Menu,
  Header
} from 'semantic-ui-react'

import ConnectionList from './list'

class Connections extends React.Component {
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

export default connect()(Connections)
