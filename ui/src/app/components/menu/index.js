//
//  index.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 10/14/19
//  Copyright 2019 Wess Cope
//

import React from 'react'

import {
  Menu, Icon
} from 'semantic-ui-react'

export default class MainMenu extends React.Component {
  constructor(props) {
    super(props)
  }

  render() {
    return (
      <Menu icon vertical inverted fluid borderless compact>
        <Menu.Item name="terminal"  active>
          <Icon name='terminal'/>
        </Menu.Item>
      </Menu>
    )
  }
}
