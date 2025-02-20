// @ts-check
//
/**
 * @namespace closure
 */

/**
 *
 * @memberof closure
 * @description A closure.
 * @typedef {object} Closure
 *
 * @property {number} someNumber - Some number.
 * @property {SomeFunction} someFunction - blah blah blah.
 *
 */


/**
 * @description Blah blah blah
 * @memberof closure
 * @callback SomeFunction
 *
 * @param {object} [options]
 * @param {number} options.count
 * @returns {void}
 */


/**
 * @returns {Closure}
 */
function Closure() {

  /** @type {SomeFunction} */
  function someFunction({ count } = { count: 1 }) {
    console.log(count)
  }
  return { someFunction, someNumber: 1 }
}


/** @type {SomeFunction} */
function whatever({ count } = { count: 1 }) { console.log(count); return }

whatever()




